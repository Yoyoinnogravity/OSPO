(function () {
  var form = document.getElementById('order');
  var vessel = document.getElementById('vessel');
  var stw = document.getElementById('stw');
  var send = document.getElementById('send');
  var ticket = document.getElementById('ticket');
  var statusEl = document.getElementById('status');
  var orderLine = document.getElementById('order-line');
  var adviceEl = document.getElementById('advice');
  var track = document.getElementById('track');
  var pollTimer = null;
  var speedTouched = false;

  var speeds = { tanker: '12', cargo: '16' };
  vessel.addEventListener('change', function () {
    if (!speedTouched) stw.value = speeds[vessel.value] || '12';
  });
  stw.addEventListener('input', function () { speedTouched = true; });

  function setStatus(state, text) {
    statusEl.className = 'status ' + (state || '');
    statusEl.textContent = text;
  }

  function fmt(p) {
    if (!p) return '';
    var ns = p.lat >= 0 ? 'N' : 'S';
    var ew = p.lon >= 0 ? 'E' : 'W';
    return Math.abs(p.lat).toFixed(2) + '°' + ns + ' ' + Math.abs(p.lon).toFixed(2) + '°' + ew;
  }

  function showOrder(order) {
    if (!order) return;
    var name = order.reference ? order.reference + ' · ' : '';
    var ship = order.vessel === 'cargo' ? 'Cargo' : 'Tanker';
    orderLine.textContent = name + ship + ' at ' + order.stwKt + ' kt, ' + fmt(order.origin) + ' to ' + fmt(order.dest);
  }

  function drawTrack(result) {
    var route = result && result.best && result.best.points && result.best.points.length > 1
      ? result.best : null;
    if (!route) { track.hidden = true; track.innerHTML = ''; return; }
    var pts = route.points;
    var lats = pts.map(function (p) { return p.lat; });
    var lons = pts.map(function (p) { return p.lon; });
    var south = Math.min.apply(null, lats);
    var north = Math.max.apply(null, lats);
    var west = Math.min.apply(null, lons);
    var east = Math.max.apply(null, lons);
    var dLat = Math.max(0.2, north - south);
    var dLon = Math.max(0.2, east - west);
    function x(lon) { return 8 + ((lon - west) / dLon) * 84; }
    function y(lat) { return 8 + ((north - lat) / dLat) * 54; }
    var d = pts.map(function (p, i) {
      return (i ? 'L' : 'M') + x(p.lon).toFixed(2) + ' ' + y(p.lat).toFixed(2);
    }).join(' ');
    var a = pts[0];
    var b = pts[pts.length - 1];
    var stroke = route.withinLimits ? '#7ec8e3' : '#f0c36a';
    track.hidden = false;
    track.innerHTML = '<path d="' + d + '" fill="none" stroke="' + stroke + '" stroke-width="1.6" stroke-linejoin="round"/>'
      + '<circle cx="' + x(a.lon).toFixed(2) + '" cy="' + y(a.lat).toFixed(2) + '" r="1.8" fill="#6bcb8b"/>'
      + '<circle cx="' + x(b.lon).toFixed(2) + '" cy="' + y(b.lat).toFixed(2) + '" r="1.8" fill="#f0c36a"/>';
  }

  function paint(job) {
    ticket.hidden = false;
    showOrder(job.order);
    if (job.status === 'queued') {
      setStatus('queued', 'Queued on the route computer.');
      adviceEl.textContent = 'Your machine is idle. The search has not started yet.';
      return;
    }
    if (job.status === 'running') {
      setStatus('running', 'The route computer is working this passage.');
      adviceEl.textContent = 'It is reading NOAA currents, wind, and waves, then timing the tracks. Leave this page open.';
      return;
    }
    if (job.status === 'failed') {
      setStatus('failed', 'The route computer stopped.');
      adviceEl.textContent = job.error || 'No advice came back.';
      track.hidden = true;
      return;
    }
    if (job.status === 'ready' && job.result) {
      setStatus('ready', job.result.ok ? 'Advice is ready.' : 'The route computer finished.');
      adviceEl.textContent = job.result.advice || '';
      drawTrack(job.result);
    }
  }

  function poll(id) {
    if (pollTimer) clearTimeout(pollTimer);
    fetch('/api/ship-route-job.php?id=' + encodeURIComponent(id), { cache: 'no-store' })
      .then(function (res) { return res.json().then(function (body) { return { res: res, body: body }; }); })
      .then(function (pack) {
        if (!pack.body || !pack.body.ok) {
          setStatus('failed', (pack.body && pack.body.error) || 'That ticket could not be read.');
          return;
        }
        paint(pack.body);
        if (pack.body.status === 'queued' || pack.body.status === 'running') {
          pollTimer = setTimeout(function () { poll(id); }, 2000);
        } else {
          send.disabled = false;
        }
      })
      .catch(function () {
        setStatus('failed', 'The passage desk did not answer.');
        send.disabled = false;
      });
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    send.disabled = true;
    adviceEl.textContent = '';
    track.hidden = true;
    setStatus('queued', 'Sending the passage…');
    ticket.hidden = false;
    fetch('/api/ship-route-job.php', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        reference: document.getElementById('reference').value,
        vessel: vessel.value,
        stwKt: Number(stw.value),
        origin: { lat: Number(document.getElementById('lat-a').value), lon: Number(document.getElementById('lon-a').value) },
        dest: { lat: Number(document.getElementById('lat-b').value), lon: Number(document.getElementById('lon-b').value) }
      })
    }).then(function (res) { return res.json(); })
      .then(function (body) {
        if (!body || !body.ok) {
          setStatus('failed', (body && body.error) || 'The passage was not accepted.');
          send.disabled = false;
          return;
        }
        if (window.history && window.history.replaceState) {
          window.history.replaceState(null, '', '/route/?job=' + body.id);
        }
        paint(body);
        poll(body.id);
      })
      .catch(function () {
        setStatus('failed', 'The passage desk did not answer.');
        send.disabled = false;
      });
  });

  var params = new URLSearchParams(window.location.search);
  var existing = params.get('job');
  if (existing) {
    send.disabled = true;
    setStatus('queued', 'Opening the ticket…');
    ticket.hidden = false;
    poll(existing);
  }
})();
