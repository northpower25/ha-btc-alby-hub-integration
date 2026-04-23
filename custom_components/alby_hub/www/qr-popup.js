(function () {
  const STATUS = document.getElementById('status');
  const STOP_BTN = document.getElementById('stop-btn');
  const CLOSE_BTN = document.getElementById('close-btn');
  const READER_ID = 'reader';
  const SOURCE = 'alby_hub_qr_popup';
  let scanner = null;
  let running = false;

  const setStatus = (msg) => {
    if (STATUS) STATUS.textContent = msg;
  };

  const postToOpener = (payload) => {
    if (!window.opener || window.opener.closed) return;
    try {
      window.opener.postMessage({ source: SOURCE, ...payload }, window.location.origin);
    } catch (err) {
      void err;
      // no-op
    }
  };

  const stopScanner = async () => {
    if (!scanner) return;
    try { if (running) await scanner.stop(); } catch (err) { void err; /* no-op */ }
    try { await scanner.clear(); } catch (err) { void err; /* no-op */ }
    running = false;
    scanner = null;
  };

  const failWith = async (message) => {
    setStatus(message);
    postToOpener({ type: 'qr_error', message });
    await stopScanner();
  };

  const start = async () => {
    setStatus('Loading scanner…');
    if (typeof window.Html5Qrcode !== 'function') {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.8/html5-qrcode.min.js';
      script.async = true;
      document.head.appendChild(script);
      await new Promise((resolve, reject) => {
        script.onload = resolve;
        script.onerror = reject;
      });
    }

    if (typeof window.Html5Qrcode !== 'function') {
      throw new Error('QR scanner library unavailable');
    }

    scanner = new window.Html5Qrcode(READER_ID);
    setStatus('Waiting for camera permission…');

    await scanner.start(
      { facingMode: 'environment' },
      { fps: 10, qrbox: 220 },
      async (decodedText) => {
        const value = String(decodedText || '').trim();
        if (!value) return;
        setStatus('QR code detected. Returning result…');
        postToOpener({ type: 'qr_result', value });
        await stopScanner();
        window.close();
      },
      () => {
        // Ignore per-frame decode misses; success callback handles valid scans.
      }
    );
    running = true;
    setStatus('Scanning…');
  };

  STOP_BTN?.addEventListener('click', async () => {
    await stopScanner();
    setStatus('Scanner stopped.');
  });

  CLOSE_BTN?.addEventListener('click', async () => {
    await stopScanner();
    window.close();
  });

  window.addEventListener('beforeunload', () => {
    void stopScanner();
  });

  void start().catch((err) => {
    const msg = String(err || '');
    const trimmed = msg.length > 120 ? `${msg.slice(0, 120)}…` : msg;
    void failWith(trimmed);
  });
})();
