/* Javascript for StudioEditableEdflexXBlock. */
function StudioEditableEdflexXBlock(runtime, element, jsonArgs) {
  "use strict";

  window.requirejs.config({
      paths: {
          'select2': jsonArgs.url_select2
      },
  });
  var initValues = jsonArgs.init_values;
  var isInit = !!initValues.resource.id;
  var resourceData = {};
  var $format = $('[name = "format"]', element);
  var $category = $('[name = "category"]', element);
  var $language = $('[name = "language"]', element);
  var $resource = $('[name = "resource"]', element);
  var $weight =  $('[name = "weight"]', element);
  var $saveButton = $('.save-button', element);
  var $featuresBlock = $('.features-block', element);

  var renderResources = function(resources) {
    if (resources.length) {
      var optionHtml = '<option value="">-------</option>';
      resources.forEach(function(resource){
        optionHtml += `<option value="${resource.resource_id}">${resource.title}</option>`;
      });
      $resource.prop('disabled', false);
      $resource.html(optionHtml);
    } else {
      $resource.empty();
      $resource.prop('disabled', true);
    }
  };

  var initResourse = function() {
    if (isInit) {
      $resource.val(initValues.resource.id);
      renderResource(initValues.resource);
      if (!$resource.val()) {
        $('.js-old-resource', element).prop('hidden', false);
      }
      isInit = false;
    }
  };

  var getListResources = function(formatValue, categoryValue, languageValue) {
    var data = {
      format: formatValue,
      category: categoryValue,
      language: languageValue
    };

    $.ajax({
      type: "POST",
      url: runtime.handlerUrl(element, 'get_list_resources'),
      data: JSON.stringify(data),
      dataType: "json",
      success: function(response) {
        renderResources(response.resources);
        initResourse();
      }
    })
  };

  var checkResources = function() {
    $saveButton.addClass('is-disabled');
    $featuresBlock.empty();
    var formatValue = $format.filter(":checked").val();
    var categoryValue = $category.val();
    var languageValue = $language.val();

    if (formatValue && categoryValue) {
      getListResources(formatValue, categoryValue, languageValue);
    } else {
      $resource.prop('disabled', true)
    }
  };

  var renderResource = function(resource) {
    var templateFeaturesList = $("#resource-template", element).html();
    $featuresBlock.html(_.template(templateFeaturesList)({
      resource: resource,
      renderDuration: renderDuration,
    }));
    resourceData = resource;
    $saveButton.removeClass('is-disabled');
  };

  var getResource = function(resource) {
    var data = {
      resource: resource,
    };

    $.ajax({
      type: "POST",
      url: runtime.handlerUrl(element, 'get_resource'),
      data: JSON.stringify(data),
      dataType: "json",
      success: function(response) {
        renderResource(response);
      }
    })
  };

  var checkResource = function()  {
    var resourceValue = $resource.val();

    if (resourceValue) {
      getResource(resourceValue);
    }
  };

  if (isInit) {
    $format.filter(`[value=${initValues.format}]`).prop('checked', true);
    $category.val(initValues.category);
    $language.val(initValues.language);
    getListResources(initValues.format, initValues.category, initValues.language)
  }

  $format.on('change', checkResources);
  $category.on('change', checkResources);
  $language.on('change', checkResources);
  $resource.on('change', checkResource);

  var studio_submit = function(data) {
    var handlerUrl = runtime.handlerUrl(element, 'submit_studio_edits');
    runtime.notify('save', {state: 'start', message: gettext("Saving")});
    $.ajax({
      type: "POST",
      url: handlerUrl,
      data: JSON.stringify(data),
      dataType: "json",
      global: false,  // Disable Studio's error handling that conflicts with studio's notify('save') and notify('cancel') :-/
      success: function(response) { runtime.notify('save', {state: 'end'}); }
    }).fail(function(jqXHR) {
      var message = gettext("This may be happening because of an error with our server or your internet connection. Try refreshing the page or making sure you are online.");
      if (jqXHR.responseText) { // Is there a more specific error message we can show?
        try {
          message = JSON.parse(jqXHR.responseText).error;
          if (typeof message === "object" && message.messages) {
            // e.g. {"error": {"messages": [{"text": "Unknown user 'bob'!", "type": "error"}, ...]}} etc.
            message = $.map(message.messages, function(msg) { return msg.text; }).join(", ");
          }
        } catch (error) { message = jqXHR.responseText.substr(0, 300); }
      }
      runtime.notify('error', {title: gettext("Unable to update settings"), message: message});
    });
  };

  $saveButton.on('click', function(e) {
    e.preventDefault();
    var weight = ($weight.val() <= 0) ? 1 : $weight.val();
    studio_submit({
      values: {
        format: $format.filter(":checked").val(),
        category: $category.val(),
        language: $language.val(),
        resource: resourceData,
        weight: weight
      },
      defaults: []
    });
  });

  $('.modal-header').append('<a class="cancel-button"><svg><use xlink:href="#icon-close"></use></svg></a>');

  $('.cancel-button').on('click', function(e) {
    e.preventDefault();
    runtime.notify('cancel', {});
  });

  require(['select2'], function() {
    $category.select2({
      placeholder: gettext("Choose a category"),
      allowClear: true
    });

    function getTitleLang(lang) {
      var titleLangs = {
        fr: 'Français',
        en: 'English',
        zh: '中文',
        ru: 'Русский',
        pt: 'Português',
        es: 'Español'
      };
      return titleLangs[lang] || lang
    }

    function langFlag(langName) {
      return $(
        '<span class="select2-flex">' +
        '<svg class="img-flag"><use xlink:href="#lang-' + langName.text + '"></use></svg>'
        + getTitleLang(langName.text) + '</span>'
      );
    }

    $language.select2({
      placeholder: gettext("Choose a language"),
      allowClear: true,
      templateResult: langFlag,
      templateSelection: langFlag
    });

    $resource.select2({
      placeholder: gettext("Select the content of your choice"),
    });
  });
}
