/* Javascript for EdflexXBlock. */
function EdflexXBlock(runtime, element) {
  var format = $('.edflex_block', element).data('format');
  var $modal = $('.js-modal-dialog', element);
  var publishGradeUrl = runtime.handlerUrl(element, 'set_grade');

  var publishGrade = function(score) {
    $.ajax({
      type: "POST",
      url: publishGradeUrl,
      data: JSON.stringify({score: score}),
    });
  };

  var openInNewTab = function(url) {
    var win = window.open(url, '_blank');
    win.focus();
  };

  if (format === 'mooc' || format === 'article') {
    $('.js-access-resource', element).on('click', function() {
      $modal.prop('hidden', false);
    });
    $('.js-confirm-access', element).on('click', function() {
      publishGrade(1);
      openInNewTab($(this).data('url'))
    });
    $('.js-close', element).on('click', function() {
      $modal.prop('hidden', true);
    })
  }

  if (format === 'video') {
    var ytPlayer;
    var duration;
    window.onYouTubeIframeAPIReady = function () {
      ytPlayer = new YT.Player('youtube-player', {
        events: {
          'onReady': onPlayerReady,
          'onStateChange': onPlayerStateChange
        }
      });
    };

    function onPlayerReady(event) {
      duration = ytPlayer.getDuration();
    }

    function onPlayerStateChange(event) {
      if (event.data === YT.PlayerState.PAUSED) {
        publishGrade(Number((ytPlayer.getCurrentTime()/duration).toFixed(1)));
      }
      if (event.data === YT.PlayerState.ENDED) {
        publishGrade(1);
      }
    }
  }

  if (format === 'podcast') {
    $('.js-access-podcast-resource', element).one('click', function() {
      $('.js-iframe-podcast').prop('hidden', false);
      $(this).prop('hidden', true);
      publishGrade(1);
    });
  }
}
