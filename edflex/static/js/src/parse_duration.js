// PnYnMnDTnHnMnS
(function() {
  var numbers = '\\d+(?:[\\.,]\\d{0,3})?';
  var weekPattern = '(' + numbers + 'W)';
  var datePattern = '(' + numbers + 'Y)?(' + numbers + 'M)?(' + numbers + 'D)?';
  var timePattern = 'T(' + numbers + 'H)?(' + numbers + 'M)?(' + numbers + 'S)?';

  var iso8601 = 'P(?:' + weekPattern + '|' + datePattern + '(?:' + timePattern + ')?)';
  var objMap = ['weeks', 'years', 'months', 'days', 'hours', 'minutes', 'seconds'];
  var pattern = new RegExp(iso8601);

  var parseDuration = function(duration) {
    return duration.match(pattern).slice(1).reduce(function (prev, next, idx) {
      prev[objMap[idx]] = parseFloat(next) || 0;
      return prev;
    }, {});
  };

  var renderDuration = function(duration) {
    var durationString = '';
    var sub = '';
    var objDuration = parseDuration(duration);

    if (objDuration.years) {
      sub = (objDuration.years === 1 ? gettext('year') : gettext('years'));
      durationString += `${objDuration.years} ${sub} `;
    }
    if (objDuration.months) {
      sub = (objDuration.months === 1 ? gettext('month') : gettext('months'));
      durationString += `${objDuration.months} ${sub} `;
    }
    if (objDuration.weeks) {
      sub = (objDuration.weeks === 1 ? gettext('week') : gettext('weeks'));
      durationString += `${objDuration.weeks} ${sub} `;
    }
    if (objDuration.days) {
      sub = (objDuration.days === 1 ? gettext('day') : gettext('days'));
      durationString += `${objDuration.days} ${sub} `;
    }
    if (objDuration.hours) {
      sub = (objDuration.hours === 1 ? gettext('hour') : gettext('hours'));
      durationString += `${objDuration.hours} ${sub} `;
    }
    if (objDuration.minutes) {
      sub = (objDuration.minutes === 1 ? gettext('minute') : gettext('minutes'));
      durationString += `${objDuration.minutes} ${sub} `;
    }
    if (objDuration.seconds) {
      sub = (objDuration.seconds === 1 ? gettext('second') : gettext('seconds'));
      durationString += `${objDuration.seconds} ${sub} `;
    }
    if (durationString) {
      durationString = `<b>${durationString}</b>${gettext('in total')}`
    }
    return durationString

  };

  window.renderDuration = renderDuration;

}());
