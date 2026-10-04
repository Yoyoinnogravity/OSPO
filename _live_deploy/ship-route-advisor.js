/**
 * A-to-B route advice for tankers and cargo ships from a NOAA field.
 *
 * Compares the straight (great-circle) track with a few port and starboard
 * offsets. Each track is timed from calm-water speed plus:
 *   - along-track NOAA surface current (altimetry ugos/vgos, m/s towards)
 *   - a head-sea penalty from WAVEWATCH III significant wave height
 *   - a head-wind penalty from GFS 10 m wind (ugrd/vgrd, m/s towards)
 *
 * WAVEWATCH III direction is the direction waves travel towards.
 * One model time is used for the whole passage (latest field, not an
 * hour-by-hour forecast). Planning aid only.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.ShipRouteAdvisor = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  var EARTH_NM = 3440.065;
  var DEG = Math.PI / 180;
  var MS_TO_KT = 1.943844;

  var VESSELS = {
    tanker: {
      id: 'tanker',
      label: 'Tanker',
      stwKt: 12,
      hsCautionM: 3.5,
      hsLimitM: 5.5,
      waveK: 0.12,
      windK: 0.035
    },
    cargo: {
      id: 'cargo',
      label: 'Cargo',
      stwKt: 16,
      hsCautionM: 4.5,
      hsLimitM: 7,
      waveK: 0.07,
      windK: 0.025
    }
  };

  function vesselProfile(id, stwKt) {
    var base = VESSELS[id] || VESSELS.cargo;
    var profile = {
      id: base.id,
      label: base.label,
      stwKt: base.stwKt,
      hsCautionM: base.hsCautionM,
      hsLimitM: base.hsLimitM,
      waveK: base.waveK,
      windK: base.windK
    };
    var speed = Number(stwKt);
    if (isFinite(speed) && speed >= 4 && speed <= 25) profile.stwKt = speed;
    return profile;
  }

  function havNm(a, b) {
    var dLat = (b.lat - a.lat) * DEG;
    var dLon = (b.lon - a.lon) * DEG;
    var s = Math.sin(dLat / 2) * Math.sin(dLat / 2)
      + Math.cos(a.lat * DEG) * Math.cos(b.lat * DEG) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 2 * EARTH_NM * Math.asin(Math.min(1, Math.sqrt(s)));
  }

  function bearingDeg(a, b) {
    var y = Math.sin((b.lon - a.lon) * DEG) * Math.cos(b.lat * DEG);
    var x = Math.cos(a.lat * DEG) * Math.sin(b.lat * DEG)
      - Math.sin(a.lat * DEG) * Math.cos(b.lat * DEG) * Math.cos((b.lon - a.lon) * DEG);
    return (Math.atan2(y, x) / DEG + 360) % 360;
  }

  function destination(p, brgDeg, distNm) {
    var delta = distNm / EARTH_NM;
    var theta = brgDeg * DEG;
    var phi1 = p.lat * DEG;
    var lam1 = p.lon * DEG;
    var phi2 = Math.asin(Math.sin(phi1) * Math.cos(delta) + Math.cos(phi1) * Math.sin(delta) * Math.cos(theta));
    var lam2 = lam1 + Math.atan2(
      Math.sin(theta) * Math.sin(delta) * Math.cos(phi1),
      Math.cos(delta) - Math.sin(phi1) * Math.sin(phi2)
    );
    var lon = lam2 / DEG;
    if (lon > 180) lon -= 360;
    if (lon < -180) lon += 360;
    return { lat: phi2 / DEG, lon: lon };
  }

  function interpolate(a, b, f) {
    var phi1 = a.lat * DEG;
    var lam1 = a.lon * DEG;
    var phi2 = b.lat * DEG;
    var lam2 = b.lon * DEG;
    var d = 2 * Math.asin(Math.min(1, Math.sqrt(
      Math.sin((phi2 - phi1) / 2) * Math.sin((phi2 - phi1) / 2)
      + Math.cos(phi1) * Math.cos(phi2) * Math.sin((lam2 - lam1) / 2) * Math.sin((lam2 - lam1) / 2)
    )));
    if (d < 1e-8) return { lat: a.lat, lon: a.lon };
    var A = Math.sin((1 - f) * d) / Math.sin(d);
    var B = Math.sin(f * d) / Math.sin(d);
    var x = A * Math.cos(phi1) * Math.cos(lam1) + B * Math.cos(phi2) * Math.cos(lam2);
    var y = A * Math.cos(phi1) * Math.sin(lam1) + B * Math.cos(phi2) * Math.sin(lam2);
    var z = A * Math.sin(phi1) + B * Math.sin(phi2);
    var lon = Math.atan2(y, x) / DEG;
    if (lon > 180) lon -= 360;
    if (lon < -180) lon += 360;
    return { lat: Math.atan2(z, Math.sqrt(x * x + y * y)) / DEG, lon: lon };
  }

  function crossesDateline(a, b) {
    return Math.abs(b.lon - a.lon) > 180;
  }

  function sampleLeg(a, b) {
    var dist = havNm(a, b);
    var n = Math.max(4, Math.min(12, Math.ceil(dist / 40)));
    var pts = [];
    for (var i = 0; i <= n; i++) pts.push(interpolate(a, b, i / n));
    return pts;
  }

  function withCourses(points) {
    var out = [];
    for (var i = 0; i < points.length; i++) {
      var nxt = points[Math.min(points.length - 1, i + 1)];
      var prv = points[Math.max(0, i - 1)];
      var course = i < points.length - 1 ? bearingDeg(points[i], nxt) : bearingDeg(prv, points[i]);
      var legNm = i < points.length - 1 ? havNm(points[i], nxt) : 0;
      out.push({ lat: points[i].lat, lon: points[i].lon, courseDeg: course, legNm: legNm });
    }
    return out;
  }

  function buildCandidates(origin, dest) {
    var dist = havNm(origin, dest);
    var brg = bearingDeg(origin, dest);
    var mid = interpolate(origin, dest, 0.5);
    var off = Math.max(8, Math.min(180, dist * 0.18));
    var specs = [{ id: 'direct', label: 'Straight line', offsetNm: 0 }];
    if (dist >= 30) {
      specs.push(
        { id: 'starboard', label: 'Starboard', offsetNm: off },
        { id: 'port', label: 'Port', offsetNm: -off },
        { id: 'starboard-wide', label: 'Wide starboard', offsetNm: off * 2 },
        { id: 'port-wide', label: 'Wide port', offsetNm: -off * 2 }
      );
    }
    return specs.map(function (spec) {
      var raw;
      if (spec.offsetNm === 0) {
        raw = sampleLeg(origin, dest);
      } else {
        var side = spec.offsetNm >= 0 ? 90 : -90;
        var wp = destination(mid, brg + side, Math.abs(spec.offsetNm));
        var leg1 = sampleLeg(origin, wp);
        var leg2 = sampleLeg(wp, dest);
        raw = leg1.concat(leg2.slice(1));
      }
      var points = withCourses(raw);
      var distanceNm = 0;
      points.forEach(function (p) { distanceNm += p.legNm; });
      return {
        id: spec.id,
        label: spec.label,
        offsetNm: spec.offsetNm,
        points: points,
        distanceNm: distanceNm
      };
    });
  }

  function boundsOf(routes, padDeg) {
    var pad = padDeg == null ? 1 : padDeg;
    var south = 90, north = -90, west = 180, east = -180;
    routes.forEach(function (route) {
      route.points.forEach(function (p) {
        if (p.lat < south) south = p.lat;
        if (p.lat > north) north = p.lat;
        if (p.lon < west) west = p.lon;
        if (p.lon > east) east = p.lon;
      });
    });
    return {
      south: Math.max(-77, south - pad),
      north: Math.min(77, north + pad),
      west: Math.max(-180, west - pad),
      east: Math.min(180, east + pad)
    };
  }

  function locate(axis, value) {
    if (value < axis[0] || value > axis[axis.length - 1]) return null;
    var i = 0;
    while (i < axis.length - 2 && axis[i + 1] < value) i++;
    var a0 = axis[i];
    var a1 = axis[i + 1];
    var t = (value - a0) / Math.max(1e-9, a1 - a0);
    return { i: i, t: t };
  }

  function bilinear(lats, lons, grid, lat, lon) {
    if (!lats || !lons || !grid || lats.length < 2 || lons.length < 2) return null;
    var row = locate(lats, lat);
    var col = locate(lons, lon);
    if (!row || !col) return null;
    var q00 = grid[row.i][col.i];
    var q01 = grid[row.i][col.i + 1];
    var q10 = grid[row.i + 1][col.i];
    var q11 = grid[row.i + 1][col.i + 1];
    if ([q00, q01, q10, q11].some(function (v) { return v == null || !isFinite(v); })) return null;
    var tx = col.t;
    var ty = row.t;
    return q00 * (1 - tx) * (1 - ty) + q01 * tx * (1 - ty) + q10 * (1 - tx) * ty + q11 * tx * ty;
  }

  /** Value of the grid cell whose centre is nearest, if the point sits in that cell. */
  function cellValue(lats, lons, grid, lat, lon) {
    if (!lats || !lons || !grid || !lats.length || !lons.length) return null;
    var i = 0;
    var best = Infinity;
    var k;
    for (k = 0; k < lats.length; k++) {
      var dLat = Math.abs(lats[k] - lat);
      if (dLat < best) { best = dLat; i = k; }
    }
    var j = 0;
    best = Infinity;
    for (k = 0; k < lons.length; k++) {
      var dLon = Math.abs(lons[k] - lon);
      if (dLon < best) { best = dLon; j = k; }
    }
    var latStep = lats.length > 1 ? Math.abs(lats[1] - lats[0]) : 0.5;
    var lonStep = lons.length > 1 ? Math.abs(lons[1] - lons[0]) : 0.5;
    if (Math.abs(lats[i] - lat) > latStep * 0.75) return null;
    if (Math.abs(lons[j] - lon) > lonStep * 0.75) return null;
    var v = grid[i] && grid[i][j];
    return (v == null || !isFinite(v)) ? null : v;
  }

  function sampleField(field, lat, lon) {
    if (!field) return null;
    var c = field.currents;
    var w = field.wind;
    var wv = field.waves;
    // Nearest water cell. Bilinear was dropping whole coastal tracks wherever one corner was land.
    var cu = c ? cellValue(c.lats, c.lons, c.u, lat, lon) : null;
    var cv = c ? cellValue(c.lats, c.lons, c.v, lat, lon) : null;
    var wu = w ? cellValue(w.lats, w.lons, w.u, lat, lon) : null;
    var wvnd = w ? cellValue(w.lats, w.lons, w.v, lat, lon) : null;
    var hs = wv ? cellValue(wv.lats, wv.lons, wv.hs, lat, lon) : null;
    var dir = wv ? cellValue(wv.lats, wv.lons, wv.dir, lat, lon) : null;
    var ocean = (cu != null && cv != null) || hs != null;
    if (!ocean && wu == null) return null;
    return {
      currentU: cu,
      currentV: cv,
      windU: wu,
      windV: wvnd,
      hsM: hs,
      waveTowardsDeg: dir
    };
  }

  function alongKt(uMs, vMs, courseDeg) {
    if (uMs == null || vMs == null) return 0;
    var east = Math.sin(courseDeg * DEG);
    var north = Math.cos(courseDeg * DEG);
    return (uMs * east + vMs * north) * MS_TO_KT;
  }

  /** 1 = head seas, 0 = beam, -1 = following. Waves travel towards waveTowardsDeg. */
  function headSea(courseDeg, waveTowardsDeg) {
    if (waveTowardsDeg == null || !isFinite(waveTowardsDeg)) return 0;
    var diff = Math.abs(((waveTowardsDeg - courseDeg + 540) % 360) - 180);
    return -Math.cos(diff * DEG);
  }

  function sogAt(sample, courseDeg, profile) {
    var current = alongKt(sample && sample.currentU, sample && sample.currentV, courseDeg);
    var windAlong = alongKt(sample && sample.windU, sample && sample.windV, courseDeg);
    var headWind = Math.max(0, -windAlong);
    var hs = sample && sample.hsM != null ? Math.max(0, sample.hsM) : 0;
    var head = Math.max(0, headSea(courseDeg, sample && sample.waveTowardsDeg));
    var waveLoss = profile.waveK * hs * hs * (0.35 + 0.65 * head);
    var windLoss = profile.windK * headWind;
    var sog = profile.stwKt + current - waveLoss - windLoss;
    return {
      sogKt: Math.max(2, sog),
      clamped: sog < 2,
      currentKt: current,
      headWindKt: headWind,
      hsM: hs,
      overLimit: sample && sample.hsM != null && sample.hsM > profile.hsLimitM
    };
  }

  function scoreRoute(route, sampleAt, profile) {
    var covered = 0;
    var missing = 0;
    var currentSum = 0;
    var windSum = 0;
    var maxHs = 0;
    var maxWind = 0;
    var over = 0;
    var hours = 0;
    var pts = route.points;
    var states = [];
    for (var i = 0; i < pts.length; i++) {
      var sample = sampleAt(pts[i].lat, pts[i].lon);
      var uncovered = !sample || ((sample.currentU == null && sample.currentV == null) && sample.hsM == null);
      if (uncovered) {
        missing++;
        states.push(null);
        continue;
      }
      covered++;
      var st = sogAt(sample, pts[i].courseDeg, profile);
      states.push(st);
      currentSum += st.currentKt;
      windSum += st.headWindKt;
      if (st.hsM > maxHs) maxHs = st.hsM;
      if (st.headWindKt > maxWind) maxWind = st.headWindKt;
      if (st.overLimit) over++;
    }
    for (var j = 0; j < pts.length - 1; j++) {
      var a = states[j];
      var b = states[j + 1];
      var sog = (a && b) ? (a.sogKt + b.sogKt) / 2 : (a ? a.sogKt : (b ? b.sogKt : profile.stwKt));
      hours += pts[j].legNm / sog;
    }
    var n = Math.max(1, covered);
    var missFrac = missing / Math.max(1, pts.length);
    return {
      id: route.id,
      label: route.label,
      offsetNm: route.offsetNm,
      points: pts,
      distanceNm: route.distanceNm,
      hours: hours + over * 4,
      sailHours: hours,
      meanCurrentKt: currentSum / n,
      meanHeadWindKt: windSum / n,
      maxHsM: maxHs,
      maxHeadWindKt: maxWind,
      overLimitSamples: over,
      withinLimits: over === 0 && missFrac <= 0.25,
      missingFrac: missFrac,
      valid: missFrac <= 0.25 && covered >= 2
    };
  }

  function fmtHours(h) {
    if (h < 48) return h.toFixed(1) + ' h';
    var d = Math.floor(h / 24);
    var rem = h - d * 24;
    return d + ' d ' + rem.toFixed(0) + ' h';
  }

  function sidePhrase(route) {
    if (!route || route.offsetNm === 0) return 'the straight line';
    if (route.id.indexOf('wide') >= 0) {
      return route.offsetNm > 0 ? 'the wide starboard track' : 'the wide port track';
    }
    return route.offsetNm > 0 ? 'the starboard track' : 'the port track';
  }

  function writeAdvice(best, direct, profile, field, compared) {
    var timeNote = (field && field.time) ? (' NOAA time ' + String(field.time).replace('T', ' ').replace('Z', ' UTC') + '.') : '';
    var gaps = [];
    if (field && !field.currents) gaps.push('currents');
    if (field && !field.wind) gaps.push('wind');
    if (field && !field.waves) gaps.push('waves');
    var gapNote = gaps.length ? (' The NOAA ' + gaps.join(' and ') + ' grid did not load, so that part was left out of the timing.') : '';
    var hold = ' This uses the latest NOAA current, wave, and wind field for the whole passage, as if it holds. It is a first look, not an hour-by-hour forecast.' + gapNote;
    var sea = ' Highest significant wave on it is ' + best.maxHsM.toFixed(1) + ' m.';
    var cur = ' Mean along-track current is ' + (best.meanCurrentKt >= 0 ? '+' : '') + best.meanCurrentKt.toFixed(1) + ' kt.';
    var ship = profile.label.toLowerCase();
    if (!best.withinLimits) {
      return 'Every usable track is rough for a ' + ship
        + ' (planning limit ' + profile.hsLimitM.toFixed(1) + ' m). The least-exposed is '
        + sidePhrase(best) + ', about ' + fmtHours(best.sailHours) + ', with seas up to '
        + best.maxHsM.toFixed(1) + ' m. Wait for a calmer NOAA field, or slow the ship.'
        + timeNote + hold;
    }
    if (!direct) {
      return 'Take ' + sidePhrase(best) + ' for this ' + ship
        + '. The straight line has no NOAA ocean values, so it was left out. About '
        + fmtHours(best.sailHours) + ' for ' + best.distanceNm.toFixed(0) + ' nm.'
        + sea + cur + timeNote + hold;
    }
    if (best.id === direct.id) {
      return 'The straight line is the best route for this ' + ship
        + ' at ' + profile.stwKt.toFixed(0) + ' kt. Moving off it does not buy time across '
        + compared + ' NOAA tracks. About ' + fmtHours(best.sailHours) + ' for '
        + best.distanceNm.toFixed(0) + ' nm.' + sea + cur + timeNote + hold;
    }
    if (!direct.withinLimits) {
      return 'For this ' + ship + ', leave the straight line. Seas on it reach '
        + direct.maxHsM.toFixed(1) + ' m, past the ' + profile.hsLimitM.toFixed(1)
        + ' m planning limit. Take ' + sidePhrase(best) + ', about ' + fmtHours(best.sailHours)
        + '.' + sea + cur + timeNote + hold;
    }
    var saved = direct.sailHours - best.sailHours;
    var quicker = saved >= 0.05
      ? (' It is ' + fmtHours(Math.abs(saved)) + ' quicker than the straight line ('
        + fmtHours(best.sailHours) + ' versus ' + fmtHours(direct.sailHours) + ').')
      : ' Time is effectively the same as the straight line, with an easier sea.';
    return 'For this ' + ship + ' at ' + profile.stwKt.toFixed(0)
      + ' kt, take ' + sidePhrase(best) + '.' + quicker + sea + cur + timeNote + hold;
  }

  function advise(opts) {
    var origin = opts.origin;
    var dest = opts.dest;
    if (!origin || !dest || !isFinite(origin.lat) || !isFinite(dest.lat)) {
      return { ok: false, advice: 'Set a departure and an arrival.' };
    }
    if (crossesDateline(origin, dest)) {
      return {
        ok: false,
        advice: 'This passage crosses the date line. Split it into two legs that each stay on one side of 180°.'
      };
    }
    var dist = havNm(origin, dest);
    if (dist < 8) {
      return { ok: false, advice: 'That leg is under 8 nm. Sail the straight line. Weather routing starts to matter on longer passages.' };
    }
    var profile = vesselProfile(opts.vessel, opts.stwKt);
    var routes = opts.candidates || buildCandidates(origin, dest);
    var sampleAt = opts.sampleAt || function (lat, lon) { return sampleField(opts.field, lat, lon); };
    var scored = routes.map(function (route) { return scoreRoute(route, sampleAt, profile); });
    var usable = scored.filter(function (r) { return r.valid; });
    if (!usable.length) {
      return {
        ok: false,
        vessel: profile,
        routes: scored,
        advice: 'NOAA has no ocean values on these tracks. They may cross land, or the current and wave grids did not load. Move the ends onto water and try again.'
      };
    }
    usable.sort(function (a, b) {
      if (a.withinLimits !== b.withinLimits) return a.withinLimits ? -1 : 1;
      return a.hours - b.hours;
    });
    var best = usable[0];
    var direct = null;
    for (var i = 0; i < scored.length; i++) if (scored[i].id === 'direct') direct = scored[i];
    return {
      ok: true,
      vessel: profile,
      best: best,
      direct: direct,
      routes: scored,
      savedHours: direct ? (direct.sailHours - best.sailHours) : 0,
      advice: writeAdvice(best, direct && direct.valid ? direct : null, profile, opts.field, usable.length)
    };
  }

  return {
    VESSELS: VESSELS,
    vesselProfile: vesselProfile,
    havNm: havNm,
    bearingDeg: bearingDeg,
    crossesDateline: crossesDateline,
    buildCandidates: buildCandidates,
    boundsOf: boundsOf,
    bilinear: bilinear,
    sampleField: sampleField,
    destination: destination,
    sogAt: sogAt,
    scoreRoute: scoreRoute,
    advise: advise
  };
});
