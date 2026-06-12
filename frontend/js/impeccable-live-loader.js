/**
 * Impeccable Live opt-in loader — does not load live.js unless explicitly enabled.
 *
 * Enable via:
 *   - URL ?impeccable=1 (persists to localStorage)
 *   - localStorage impeccable-live=1
 *   - Shift+Alt+I or triple-click the「2711编辑器」brand
 *
 * Disable: ?impeccable=0 or localStorage.removeItem('impeccable-live')
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'impeccable-live';
  var PORT_KEY = 'impeccable-live-port';
  var DEFAULT_PORT = 8400;

  function getPort() {
    try {
      var loader = document.querySelector('script[src*="impeccable-live-loader"]');
      var fromTag = loader && loader.getAttribute('data-impeccable-port');
      if (fromTag && /^\d+$/.test(fromTag)) return parseInt(fromTag, 10);

      var params = new URLSearchParams(window.location.search);
      var fromUrl = params.get('port');
      if (fromUrl && /^\d+$/.test(fromUrl)) {
        localStorage.setItem(PORT_KEY, fromUrl);
        return parseInt(fromUrl, 10);
      }
      var stored = localStorage.getItem(PORT_KEY);
      if (stored && /^\d+$/.test(stored)) return parseInt(stored, 10);
    } catch (_) {}
    return DEFAULT_PORT;
  }

  function shouldEnable() {
    try {
      var params = new URLSearchParams(window.location.search);
      if (params.get('impeccable') === '0') {
        localStorage.removeItem(STORAGE_KEY);
        return false;
      }
      if (params.get('impeccable') === '1') {
        localStorage.setItem(STORAGE_KEY, '1');
        return true;
      }
      return localStorage.getItem(STORAGE_KEY) === '1';
    } catch (_) {
      return false;
    }
  }

  function loadLive() {
    if (document.querySelector('script[data-impeccable-live-loader]')) return;
    var port = getPort();
    var script = document.createElement('script');
    script.src = 'http://localhost:' + port + '/live.js';
    script.dataset.impeccableLiveLoader = '1';
    document.body.appendChild(script);
  }

  function enableLive() {
    try {
      localStorage.setItem(STORAGE_KEY, '1');
    } catch (_) {}
    loadLive();
  }

  if (shouldEnable()) loadLive();

  document.addEventListener('keydown', function (e) {
    if (e.shiftKey && e.altKey && (e.key === 'I' || e.key === 'i')) {
      e.preventDefault();
      enableLive();
    }
  });

  var clickCount = 0;
  var clickTimer = null;
  document.addEventListener('click', function (e) {
    var brand = e.target.closest && e.target.closest('.workbench__brand, .workbench__brand-zh');
    if (!brand) return;
    clickCount += 1;
    clearTimeout(clickTimer);
    clickTimer = setTimeout(function () {
      clickCount = 0;
    }, 600);
    if (clickCount >= 3) {
      clickCount = 0;
      enableLive();
    }
  });
})();
