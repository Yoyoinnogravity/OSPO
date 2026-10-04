/**
 * Isochrone prediction for a tanker or cargo passage.
 *
 * The ship is stepped through the NOAA forecast. Each step tries a fan of
 * courses and two speeds, samples wind, waves, and current at the ship's
 * own time, and keeps the earliest arrival in each patch of sea.
 * Wind and waves change with the forecast. Daily altimetry currents are held.
 *
 * This is a planning model (wave-height and head-wind speed loss). It is not
 * a ship-motion study. The master still owns the voyage.
 */
(function (root, factory) {
  var api = factory(typeof require !== 'undefined' ? require('./ship-route-advisor.js') : root.ShipRouteAdvisor);
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.ShipRoutePredict = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function (Advisor) {
  var EARTH_NM = 3440.065;
  var DEG = Math.PI / 180;

  function fmtHours(h) {
    if (h < 48) return h.toFixed(1) + ' h';
    var d = Math.floor(h / 24);
    var rem = h - d * 24;
    return d + ' d ' + rem.toFixed(0) + ' h';
  }

  function num(n) {
    return String(Math.round(n));
  }

  function lerp(a, b, u) {
    if (a == null || !isFinite(a)) return b;
    if (b == null || !isFinite(b)) return a;
    return a + (b - a) * u;
  }

  function lerpAngle(a, b, u) {
    if (a == null || !isFinite(a)) return b;
    if (b == null || !isFinite(b)) return a;
    var d = ((b - a + 540) % 360) - 180;
    return (a + d * u + 360) % 360;
  }

  function crossTrackNm(origin, dest, p) {
    var d13 = Advisor.havNm(origin, p) / EARTH_NM;
    var th13 = Advisor.bearingDeg(origin, p) * DEG;
    var th12 = Advisor.bearingDeg(origin, dest) * DEG;
    return Math.abs(Math.asin(Math.max(-1, Math.min(1, Math.sin(d13) * Math.sin(th13 - th12))))) * EARTH_NM;
  }

  function alongTrackNm(origin, dest, p) {
    var d13 = Advisor.havNm(origin, p) / EARTH_NM;
    var th13 = Advisor.bearingDeg(origin, p) * DEG;
    var th12 = Advisor.bearingDeg(origin, dest) * DEG;
    var xt = Math.asin(Math.max(-1, Math.min(1, Math.sin(d13) * Math.sin(th13 - th12))));
    var cosXt = Math.cos(xt);
    if (Math.abs(cosXt) < 1e-6) return 0;
    var along = Math.acos(Math.max(-1, Math.min(1, Math.cos(d13) / cosXt)));
    var behind = Math.cos(th13 - th12) < 0;
    return (behind ? -along : along) * EARTH_NM;
  }

  function inCorridor(origin, dest, p, corridorNm, distNm) {
    if (crossTrackNm(origin, dest, p) > corridorNm) return false;
    var along = alongTrackNm(origin, dest, p);
    return along > -Math.min(40, corridorNm) && along < distNm + corridorNm * 0.35;
  }

  function prepareFrames(frames) {
    var out = [];
    (frames || []).forEach(function (frame) {
      if (!frame) return;
      var ms = Date.parse(frame.time);
      out.push({
        time: frame.time,
        timeMs: isFinite(ms) ? ms : null,
        currents: frame.currents || null,
        wind: frame.wind || null,
        waves: frame.waves || null
      });
    });
    out.sort(function (a, b) { return (a.timeMs || 0) - (b.timeMs || 0); });
    if (out.length && out[0].timeMs == null) {
      var t0 = Date.now();
      out.forEach(function (frame, i) { frame.timeMs = t0 + i * 6 * 3600000; });
    }
    return out;
  }

  function sampleAtTime(frames, lat, lon, timeMs) {
    if (!frames.length) return null;
    var i = 0;
    if (frames.length > 1 && timeMs != null) {
      while (i < frames.length - 2 && frames[i + 1].timeMs <= timeMs) i++;
    }
    var a = frames[Math.min(i, frames.length - 1)];
    var b = frames[Math.min(i + 1, frames.length - 1)];
    var span = b.timeMs - a.timeMs;
    var u = (a === b || !span || timeMs == null) ? 0 : (timeMs - a.timeMs) / span;
    if (u < 0) u = 0;
    if (u > 1) u = 1;
    var sa = Advisor.sampleField(a, lat, lon);
    var sb = a === b ? sa : Advisor.sampleField(b, lat, lon);
    if (!sa) return sb;
    if (!sb || u === 0) return sa;
    return {
      currentU: lerp(sa.currentU, sb.currentU, u),
      currentV: lerp(sa.currentV, sb.currentV, u),
      windU: lerp(sa.windU, sb.windU, u),
      windV: lerp(sa.windV, sb.windV, u),
      hsM: lerp(sa.hsM, sb.hsM, u),
      waveTowardsDeg: lerpAngle(sa.waveTowardsDeg, sb.waveTowardsDeg, u)
    };
  }

  function onWater(sample) {
    if (!sample) return false;
    var current = sample.currentU != null && sample.currentV != null;
    return current || sample.hsM != null;
  }

  function searchBounds(origin, dest) {
    var dist = Advisor.havNm(origin, dest);
    var corridorNm = Math.max(60, Math.min(480, dist * 0.4));
    var pad = corridorNm / 60 + 0.35;
    return {
      south: Math.max(-77, Math.min(origin.lat, dest.lat) - pad),
      north: Math.min(77, Math.max(origin.lat, dest.lat) + pad),
      west: Math.max(-180, Math.min(origin.lon, dest.lon) - pad),
      east: Math.min(180, Math.max(origin.lon, dest.lon) + pad)
    };
  }

  function horizonHours(distNm, stwKt) {
    var h = distNm / Math.max(4, stwKt) * 1.8 + 8;
    return Math.max(18, Math.min(120, Math.round(h)));
  }

  function cellKey(lat, lon, cell) {
    return Math.round(lat / cell) + ':' + Math.round(lon / cell);
  }

  function limitsFor(profile, speedFactor) {
    var limit = profile.hsLimitM * (speedFactor < 0.85 ? 1.2 : 1);
    return limit;
  }

  function stepState(sample, course, profile, speedFactor) {
    var local = {
      id: profile.id,
      label: profile.label,
      stwKt: profile.stwKt * speedFactor,
      hsCautionM: profile.hsCautionM,
      hsLimitM: profile.hsLimitM,
      waveK: profile.waveK,
      windK: profile.windK
    };
    var st = Advisor.sogAt(sample, course, local);
    st.overLimit = sample.hsM != null && sample.hsM > limitsFor(profile, speedFactor);
    st.speedFactor = speedFactor;
    return st;
  }

  function sailDirect(origin, dest, profile, frames, dtHours) {
    var pos = { lat: origin.lat, lon: origin.lon };
    var t = frames[0].timeMs;
    var hours = 0;
    var maxHs = 0;
    var currentSum = 0;
    var n = 0;
    var over = 0;
    var travelled = 0;
    var points = [{ lat: origin.lat, lon: origin.lon }];
    var guard = 0;
    while (Advisor.havNm(pos, dest) > 6 && guard < 240) {
      guard++;
      var course = Advisor.bearingDeg(pos, dest);
      var sample = sampleAtTime(frames, pos.lat, pos.lon, t);
      if (!onWater(sample)) {
        return { id: 'direct', label: 'Straight line', valid: false, points: points, offsetNm: 0 };
      }
      var st = stepState(sample, course, profile, 1);
      var remain = Advisor.havNm(pos, dest);
      var stepNm = Math.min(remain, Math.max(2, st.sogKt) * dtHours);
      var nxt = stepNm >= remain - 0.05 ? { lat: dest.lat, lon: dest.lon } : Advisor.destination(pos, course, stepNm);
      var leg = Advisor.havNm(pos, nxt);
      var h = leg / Math.max(2, st.sogKt);
      hours += h;
      t += h * 3600000;
      travelled += leg;
      if (st.hsM > maxHs) maxHs = st.hsM;
      currentSum += st.currentKt;
      n++;
      if (st.overLimit) over++;
      pos = nxt;
      points.push({ lat: pos.lat, lon: pos.lon });
    }
    return {
      id: 'direct',
      label: 'Straight line',
      offsetNm: 0,
      valid: n >= 1 && Advisor.havNm(pos, dest) <= 8,
      points: points,
      distanceNm: travelled,
      sailHours: hours,
      meanCurrentKt: n ? currentSum / n : 0,
      maxHsM: maxHs,
      withinLimits: over === 0,
      overLimitSamples: over
    };
  }

  function pathOf(node) {
    var pts = [];
    var guard = 0;
    while (node && guard < 500) {
      pts.push({ lat: node.lat, lon: node.lon });
      if (!node.parent || node.parent === node) break;
      node = node.parent;
      guard++;
    }
    pts.reverse();
    return pts;
  }

  /** Within a quarter-hour, stay nearer the straight line. Leave it when the sea makes that late. */
  function betterReach(child, prev, origin, dest) {
    var dtH = (child.timeMs - prev.timeMs) / 3600000;
    if (Math.abs(dtH) < 0.25) {
      return crossTrackNm(origin, dest, child) + 1 < crossTrackNm(origin, dest, prev);
    }
    return dtH < 0;
  }

  function maxCross(points, origin, dest) {
    var m = 0;
    points.forEach(function (p) {
      var x = crossTrackNm(origin, dest, p);
      if (x > m) m = x;
    });
    return m;
  }

  /**
   * @param {object} opts origin, dest, vessel, stwKt, frames, onProgress
   */
  function predictPassage(opts) {
    var origin = opts.origin;
    var dest = opts.dest;
    if (!origin || !dest) return { ok: false, advice: 'Set a departure and an arrival.' };
    if (Advisor.crossesDateline(origin, dest)) {
      return { ok: false, advice: 'This passage crosses the date line. Split it into two legs that each stay on one side of 180°.' };
    }
    var dist = Advisor.havNm(origin, dest);
    if (dist < 8) {
      return { ok: false, advice: 'That leg is under 8 nm. Sail the straight line. Weather routing starts to matter on longer passages.' };
    }
    var frames = prepareFrames(opts.frames);
    if (!frames.length) return { ok: false, advice: 'The route computer has no NOAA forecast to predict with.' };
    var profile = Advisor.vesselProfile(opts.vessel, opts.stwKt);
    var departSample = sampleAtTime(frames, origin.lat, origin.lon, frames[0].timeMs);
    if (!onWater(departSample)) {
      return {
        ok: false,
        advice: 'NOAA has no ocean values at the departure. Move it onto water. Wind over land is not enough to predict a route.'
      };
    }

    var dt = dist > 1800 ? 3 : 2;
    // A step spans about three cells, so two courses do not collapse into one patch.
    var cell = Math.max(0.1, Math.min(0.35, (profile.stwKt * dt / 60) / 3));
    var corridor = Math.max(60, Math.min(480, dist * 0.4));
    var arrivalNm = Math.max(18, profile.stwKt * dt * 0.7);
    var maxSteps = Math.min(80, Math.ceil(dist / (profile.stwKt * dt) * 2.6) + 8);
    var headings = [];
    var hdg;
    for (hdg = -80; hdg <= 80; hdg += 10) headings.push(hdg);
    var speeds = [1, 0.72];
    var started = Date.now();

    function search(allowOver) {
      var best = new Map();
      var start = {
        key: cellKey(origin.lat, origin.lon, cell),
        lat: origin.lat,
        lon: origin.lon,
        timeMs: frames[0].timeMs,
        parent: null,
        distNm: 0,
        maxHs: 0,
        currentSum: 0,
        samples: 0,
        over: 0
      };
      best.set(start.key, start);
      var frontier = [start.key];
      var arrival = null;
      var predictions = 0;

      for (var step = 1; step <= maxSteps && frontier.length; step++) {
        var next = [];
        var seen = {};
        for (var f = 0; f < frontier.length; f++) {
          var node = best.get(frontier[f]);
          if (!node) continue;
          if (arrival && node.timeMs >= arrival.timeMs) continue;
          var remain0 = Advisor.havNm(node, dest);
          if (remain0 <= arrivalNm) {
            arrival = finish(node, remain0, profile, frames, arrival);
            continue;
          }
          var brg = Advisor.bearingDeg(node, dest);
          for (var hi = 0; hi < headings.length; hi++) {
            var course = (brg + headings[hi] + 360) % 360;
            for (var si = 0; si < speeds.length; si++) {
              predictions++;
              var sample = sampleAtTime(frames, node.lat, node.lon, node.timeMs);
              if (!onWater(sample)) continue;
              var st = stepState(sample, course, profile, speeds[si]);
              if (st.overLimit && !allowOver) continue;
              var stepNm = Math.max(2, st.sogKt) * dt;
              var remain = Advisor.havNm(node, dest);
              var pos;
              var leg;
              if (remain <= stepNm && Math.abs(headings[hi]) <= 40) {
                pos = { lat: dest.lat, lon: dest.lon };
                leg = remain;
              } else {
                pos = Advisor.destination(node, course, stepNm);
                leg = stepNm;
              }
              if (!inCorridor(origin, dest, pos, corridor, dist)) continue;
              var endSample = sampleAtTime(frames, pos.lat, pos.lon, node.timeMs + (leg / Math.max(2, st.sogKt)) * 3600000);
              if (!onWater(endSample)) continue;
              var endState = stepState(endSample, course, profile, speeds[si]);
              if (endState.overLimit && !allowOver) continue;
              var sog = Math.max(2, (st.sogKt + endState.sogKt) / 2);
              var hours = leg / sog;
              var timeMs = node.timeMs + hours * 3600000;
              var hs = Math.max(st.hsM || 0, endState.hsM || 0);
              var over = node.over + ((st.overLimit || endState.overLimit) ? 1 : 0);
              var child = {
                key: cellKey(pos.lat, pos.lon, cell),
                lat: pos.lat,
                lon: pos.lon,
                timeMs: timeMs,
                parent: node,
                distNm: node.distNm + leg,
                maxHs: Math.max(node.maxHs, hs),
                currentSum: node.currentSum + (st.currentKt + endState.currentKt) / 2,
                samples: node.samples + 1,
                over: over
              };
              if (Advisor.havNm(pos, dest) <= arrivalNm) {
                arrival = finish(child, Advisor.havNm(pos, dest), profile, frames, arrival);
              }
              var prev = best.get(child.key);
              if (prev && !betterReach(child, prev, origin, dest)) continue;
              best.set(child.key, child);
              if (!seen[child.key]) {
                seen[child.key] = true;
                next.push(child.key);
              }
            }
          }
        }
        frontier = next;
        if (opts.onProgress) {
          opts.onProgress({
            phase: 'predicting',
            step: step,
            steps: maxSteps,
            predictions: predictions,
            frontier: frontier.length,
            frames: frames.length
          });
        }
        if (arrival) {
          var earliest = Infinity;
          for (var n = 0; n < frontier.length; n++) {
            var nd = best.get(frontier[n]);
            if (nd && nd.timeMs < earliest) earliest = nd.timeMs;
          }
          if (earliest >= arrival.timeMs) break;
        }
      }
      return { arrival: arrival, predictions: predictions };
    }

    function finish(node, remainNm, profile, frames, prev) {
      var course = Advisor.bearingDeg(node, dest);
      var sample = sampleAtTime(frames, node.lat, node.lon, node.timeMs);
      var st = onWater(sample) ? stepState(sample, course, profile, 1) : null;
      var sog = st ? Math.max(2, st.sogKt) : profile.stwKt;
      var extra = remainNm / sog;
      var over = node.over + (st && st.overLimit ? 1 : 0);
      var candidate = {
        key: 'arrival',
        lat: dest.lat,
        lon: dest.lon,
        timeMs: node.timeMs + extra * 3600000,
        parent: node.parent && node.lat === dest.lat ? node.parent : node,
        distNm: node.distNm + remainNm,
        maxHs: Math.max(node.maxHs, st ? st.hsM : 0),
        currentSum: node.currentSum + (st ? st.currentKt : 0),
        samples: node.samples + (st ? 1 : 0),
        over: over,
        withinLimits: over === 0
      };
      if (!prev) return candidate;
      if (candidate.withinLimits !== prev.withinLimits) return candidate.withinLimits ? candidate : prev;
      return candidate.timeMs < prev.timeMs ? candidate : prev;
    }

    var found = search(false);
    if (!found.arrival || !found.arrival.withinLimits) {
      var rough = search(true);
      found.predictions += rough.predictions;
      if (!found.arrival || (rough.arrival && rough.arrival.withinLimits)) found.arrival = rough.arrival || found.arrival;
      else if (rough.arrival && !found.arrival.withinLimits && rough.arrival.timeMs < found.arrival.timeMs) found.arrival = rough.arrival;
    }

    var direct = sailDirect(origin, dest, profile, frames, dt);
    if (!found.arrival) {
      return {
        ok: false,
        vessel: profile,
        direct: direct.valid ? direct : null,
        stats: { predictions: found.predictions, frames: frames.length, dtHours: dt },
        advice: 'The route computer checked ' + num(found.predictions)
          + ' positions and did not reach the arrival inside the forecast corridor. The sea may be closed, or the ends are on land.'
      };
    }

    var points = pathOf(found.arrival);
    if (!points.length || Advisor.havNm(points[points.length - 1], dest) > 1) {
      points.push({ lat: dest.lat, lon: dest.lon });
    }
    var sailH = (found.arrival.timeMs - frames[0].timeMs) / 3600000;
    var cross = maxCross(points, origin, dest);
    var onLine = cross < 22 && direct.valid;
    var best = {
      id: onLine ? 'direct' : 'predicted',
      label: onLine ? 'Straight line' : 'Predicted route',
      offsetNm: onLine ? 0 : Math.round(cross),
      points: points,
      distanceNm: found.arrival.distNm,
      sailHours: sailH,
      meanCurrentKt: found.arrival.samples ? found.arrival.currentSum / found.arrival.samples : 0,
      maxHsM: found.arrival.maxHs,
      withinLimits: !!found.arrival.withinLimits,
      valid: true
    };
    var lastMs = frames[frames.length - 1].timeMs;
    var held = found.arrival.timeMs > lastMs + 3 * 3600000;
    var stats = {
      predictions: found.predictions,
      frames: frames.length,
      dtHours: dt,
      cellDeg: cell,
      corridorNm: Math.round(corridor),
      heldLastFrame: held && frames.length > 1,
      singleFrame: frames.length === 1,
      elapsedMs: Date.now() - started
    };
    var routes = [best];
    if (direct.valid && best.id !== 'direct') routes.push(direct);
    return {
      ok: true,
      vessel: profile,
      best: best,
      direct: direct.valid ? direct : null,
      routes: routes,
      savedHours: direct.valid ? (direct.sailHours - best.sailHours) : 0,
      stats: stats,
      advice: writePrediction(best, direct.valid ? direct : null, profile, stats, cross)
    };
  }

  function writePrediction(best, direct, profile, stats, cross) {
    var ship = profile.label.toLowerCase();
    var work = ' The route computer checked ' + num(stats.predictions) + ' positions, '
      + stats.dtHours + ' hours at a step, through ' + stats.frames + ' NOAA forecast time'
      + (stats.frames === 1 ? '' : 's') + '.';
    var weak = stats.singleFrame
      ? ' Only one forecast time was available, so that sea state is held for the whole passage.'
      : '';
    var held = stats.heldLastFrame
      ? ' The forecast ends before arrival, so the last wind and wave map is held after that.'
      : '';
    var model = ' Daily altimetry currents are held. Speed loss is a planning model from wave height and head wind, not a ship-motion study.';
    var sea = ' Highest significant wave on the predicted track is ' + best.maxHsM.toFixed(1) + ' m.';
    var timeNote = work + weak + held + ' ' + model;

    if (!best.withinLimits) {
      return 'No predicted track stays inside the ' + profile.hsLimitM.toFixed(1)
        + ' m planning limit for this ' + ship + '. The least-late track still meets '
        + best.maxHsM.toFixed(1) + ' m seas and takes about ' + fmtHours(best.sailHours)
        + '. Wait, or slow the ship further.' + timeNote;
    }
    if (!direct) {
      if (cross < 22) {
        return 'For this ' + ship + ', the predicted route stays close to the straight line, on water the NOAA grid can see. About '
          + fmtHours(best.sailHours) + ' for ' + best.distanceNm.toFixed(0) + ' nm. ' + sea + timeNote;
      }
      return 'Take the predicted route for this ' + ship + '. The straight line does not stay on water in the NOAA grid. About '
        + fmtHours(best.sailHours) + ' for ' + best.distanceNm.toFixed(0) + ' nm. ' + sea + timeNote;
    }
    if (best.id === 'direct') {
      return 'The straight line is the predicted route for this ' + ship + ' at '
        + profile.stwKt.toFixed(0) + ' kt. Courses off the line did not arrive sooner inside the sea limit. About '
        + fmtHours(best.sailHours) + ' for ' + best.distanceNm.toFixed(0) + ' nm. ' + sea + timeNote;
    }
    if (!direct.withinLimits) {
      return 'For this ' + ship + ', leave the straight line. The prediction puts '
        + direct.maxHsM.toFixed(1) + ' m seas on it, past the ' + profile.hsLimitM.toFixed(1)
        + ' m planning limit. Take the predicted route, about ' + fmtHours(best.sailHours)
        + ', ' + Math.abs(best.sailHours - direct.sailHours).toFixed(1) + ' h '
        + (best.sailHours > direct.sailHours ? 'slower' : 'quicker')
        + ' than forcing the straight line. ' + sea + timeNote;
    }
    var saved = direct.sailHours - best.sailHours;
    if (saved >= 0.3) {
      return 'For this ' + ship + ' at ' + profile.stwKt.toFixed(0)
        + ' kt, take the predicted route. It is ' + saved.toFixed(1)
        + ' h quicker than the straight line (' + fmtHours(best.sailHours) + ' versus '
        + fmtHours(direct.sailHours) + '). ' + sea + timeNote;
    }
    return 'For this ' + ship + ', the predicted route and the straight line are within half an hour. About '
      + fmtHours(best.sailHours) + '. ' + sea + timeNote;
  }

  return {
    searchBounds: searchBounds,
    horizonHours: horizonHours,
    sampleAtTime: sampleAtTime,
    predictPassage: predictPassage,
    crossTrackNm: crossTrackNm
  };
});
