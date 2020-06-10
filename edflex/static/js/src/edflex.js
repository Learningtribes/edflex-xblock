/* Javascript for EdflexXBlock. */
function EdflexXBlock(runtime, element) {
  var format = $('.edflex_block', element).data('format');
  var $modal = $('.js-modal-dialog', element);
  var $modalOverlay = $('.js-modal-overlay', element);
  var $resourceDuration = $('.js-resource-duration', element);
  var publishGradeUrl = runtime.handlerUrl(element, 'set_grade');

  if ($resourceDuration.length) {
    var duration = renderDuration($resourceDuration.data('duration'));
    $resourceDuration.html(duration);
  }

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

  if (format === 'mooc' || format === 'article' || format === 'book') {
    $('.js-access-resource', element).on('click', function() {
      $modal.prop('hidden', false);
      $modalOverlay.prop('hidden', false);
    });
    $('.js-confirm-access', element).on('click', function() {
      publishGrade(1);
      openInNewTab($(this).data('url'));
      $modal.prop('hidden', true);
      $modalOverlay.prop('hidden', true);
    });
    $('.js-close', element).on('click', function() {
      $modal.prop('hidden', true);
      $modalOverlay.prop('hidden', true);
    })
  }

  if (format === 'video') {
    var ytPlayer;
    var videoDuration;
    window.onYouTubeIframeAPIReady = function () {
      ytPlayer = new YT.Player('youtube-player', {
        events: {
          'onReady': onPlayerReady,
          'onStateChange': onPlayerStateChange
        }
      });
    };

    function onPlayerReady(event) {
      videoDuration = ytPlayer.getDuration();
    }

    function onPlayerStateChange(event) {
      if (event.data === YT.PlayerState.PAUSED) {
        if (ytPlayer.getCurrentTime()/videoDuration >= 0.5) {
          publishGrade(1);
        }
      }
      if (event.data === YT.PlayerState.ENDED) {
        publishGrade(1);
      }
    }
  }

  if (format === 'podcast') {
    publishGrade(1);
  }
}
