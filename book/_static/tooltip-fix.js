// Keep Bootstrap tooltips from getting stuck on screen.
//
// The theme's header buttons use Bootstrap 4 tooltips, which open on hover or focus.
// On touch screens there is no hover, so a tap focuses the button and leaves its tooltip
// open; if the tap navigates away, Safari restores the page from its back/forward cache
// with the tooltip still showing.
//
// This file loads before the theme's bootstrap.js, so the tooltip plugin is looked up
// inside the handlers, which only run once every script has loaded.
(function () {
  var selector = '[data-toggle="tooltip"]';

  var tooltips = function () {
    var $ = window.jQuery;
    return $ && $.fn && $.fn.tooltip ? $(selector) : null;
  };

  var hideAll = function () {
    var $tips = tooltips();
    if ($tips) $tips.tooltip('hide');
    document.querySelectorAll('.tooltip').forEach(function (el) {
      el.remove();
    });
    if (document.activeElement && document.activeElement.blur) {
      document.activeElement.blur();
    }
  };

  // Leaving the page, and coming back to it (including back/forward cache restores).
  window.addEventListener('pagehide', hideAll);
  window.addEventListener('pageshow', hideAll);

  // On touch-only devices tooltips cannot be dismissed and only repeat the button's
  // accessible label, so turn them off once the theme has initialised them.
  var touchOnly = window.matchMedia && window.matchMedia('(hover: none)').matches;
  if (touchOnly) {
    window.addEventListener('load', function () {
      var $tips = tooltips();
      if ($tips) $tips.tooltip('disable');
    });
  }
})();
