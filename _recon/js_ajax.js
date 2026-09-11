/*
 name: jQuery ajax
 desc: Server side data access
 */
define(['settings'], function (settings) {
    var language = settings.i18n;
    var defaultOpts = {
        contentType: "application/x-www-form-urlencoded;charset=UTF-8",
        type: "POST",
        cache: false,
        data: {},
        timeout: 60000,
        dataType: "json",
        traditional: false
    };

    return {
        // ajax main method
        invoke: function (options) {
            var self = this,
                opts = $.extend({}, defaultOpts, options || {});

            self.loadingShow(options);

            self.xhr = $.ajax({
                url: opts.url,
                contentType: opts.contentType,
                type: opts.type,
                cache: opts.cache,
                data: opts.data,
                timeout: opts.timeout,
                dataType: opts.dataType,
                traditional: opts.traditional,
                success: function (result) {
                    self.success(opts, result);
                },
                error: function (error) {
                    self.errorHandler(opts, error);
                }
            });

            return self.xhr;
        },

        errorHandler:function(opts, error){
            var me = this;

            switch(error.status){
        	case 401:
        	    alert(language['12551'] + ', ' + language['10308']+'. url='+opts.url);
                    location.href = location.href;
        	    break;
            case 403:
                // forbidden
                break;
        	case 500:
        	    alert(language['10215']+':'+opts.url);
        	    break;
        	default:
        	    break;
            };
        },

        // ajax success callback
        success: function (options, result) {
            var self = this;
            if (typeof result.success === "undefined") {
                options.onsuccess(result);
                return;
            }
            self.loadingHide(options);
            if (result.success) {
                options.onsuccess(result);
            } else {
                self.failed(options, result.msg || language['10309'] + "：‘" + language['10310'] + "。’");
            }
        },

        // error callback
        error: function (options, error) {
            var self = this;
            if (options.onerror === "function") {
                options.onerror();
                return;
            }
            self.loadingHide(options);
            self.failed(options, error);
        },

        // failed callback
        failed: function (options, error) {
            var self = this;

            if (typeof options.onfailed === "function") {
                options.onfailed({ reason: error });
            }
        },

        // loading show
        loadingShow: function (options) {
            if (typeof options.loadingShow === "function") {
                options.loadingShow();
            }
        },

        // loading hide
        loadingHide: function (options) {
            if (typeof options.loadingHide === "function") {
                options.loadingHide();
            }
        }
    };

});
