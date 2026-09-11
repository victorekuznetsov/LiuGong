define(["ajax", "settings"], function (ajax, settings) {
    var language = settings.i18n;
    var loadSearchUrl = settings.actions.loadSearchUrl || "",
        modelValidateUrl = settings.actions.modelValidateUrl || "",
        modelLoadUsageUrl = settings.actions.modelLoadUsageUrl || "",
        partPhotoUrl = settings.actions.partPhotoUrl || "",
        vinValidateUrl = settings.actions.vinValidateUrl || "",
        vinLoadUsageUrl = settings.actions.vinLoadUsageUrl || "",
        searchStatus = settings.context.searchStatus;

    var defaultOpts = {
        searchTypeId: "search-type",
        searchBoxId: "search-box",
        searchButtonId: "btn-search",
        advancedSearchId: "advanced-search",
        replacementId: "",
        configureInfoId: "",
        partSerialNumberId: "",
        callbacks: {
            onAdvancedSearch: null
        }
    };

    var Search = function (options) {
        this.opts = $.extend(true, defaultOpts, options || {});
        this.searchType = "vin";

        this.init();
    };

    Search.prototype = {

        init: function () {
            var self = this;

            self.buildDomEls();
            self.bindEvent();
            self.fillSearch();
        },

        buildDomEls: function () {
            var self = this;

            self.$searchType = $("#" + self.opts.searchTypeId);
            self.$searchBox = $("#" + self.opts.searchBoxId);
            self.$searchButton = $("#" + self.opts.searchButtonId);
            self.$advancedSearch = $("#" + self.opts.advancedSearchId);
            self.$replacement = $("#" + self.opts.replacementId);
            self.$configureInfo = $("#" + self.opts.configureInfoId);
            self.$partSerialNumber = $("#" + self.opts.partSerialNumberId);
        },

        bindEvent: function () {
            var self = this, action;

            self.$searchType.on("click", "li[data-action]", function (e) {
                action = $(this).attr("data-action");
                self.changeSearchType(action);
            });

            self.$searchBox.on("keyup", function (e) {
                if (e.keyCode === 13) self.doSearch();
            });

            self.$searchButton.on("click", function () {
                self.doSearch();
            });

            self.$advancedSearch.on("click", function () {
                self.doAdvancedSearch();
            });

            self.$replacement.on("click", function () {
                // TODO
            });

            self.$configureInfo.on("click", function () {
                // TODO
            });

            self.$partSerialNumber.on("click", function () {
                // TODO
            });
        },

        fillSearch: function () {
            var self = this;

            if (searchStatus.keyword.length > 0) {
                self.$searchBox.val(searchStatus.keyword);
            }
            if (searchStatus.type.length > 0) {
                self.changeSearchType(searchStatus.type);
            }
        },

        changeSearchType: function (action) {
            var self = this,
                $sender = self.$searchType.find("li[data-action='" + action + "']");

            self.searchType = action;
            self.$searchType.find("li").removeClass("search-selected");
            $sender.addClass("search-selected");
        },

        doSearch: function () {
            var self = this,
                params = {},
                keyword = self.$searchBox.val();

            if ($.trim(keyword).length === 0) {
                alert(language['10269']);
                self.$searchBox.focus();
                return;
            }

            switch (self.searchType) {
                case "vin":
                    self.validateVin(keyword);
                    break;
                case "modelCode":
                    self.validateModel(keyword);
                    break;
                case "partPhoto"://wbw add 20190411 打开零件照片
                    window.open(partPhotoUrl +"/?partNO="+ keyword,"_blank");
                    break;
                default:
                    params[self.searchType] = keyword;
                    self.doAdvancedSearch(params);
                    break;
            }
            ;
        },

        validateVin: function (keyword) {
            var self = this;

            ajax.invoke({
                url: vinValidateUrl,
                data: "code=" + keyword,
                contentType: "application/json",
                type: "get",
                onsuccess: function (root) {
                    self.vinToLoadUsage(root, keyword);
                }
            });
        },

        validateModel: function (keyword) {
            var self = this;

            ajax.invoke({
                url: modelValidateUrl,
                data: "code=" + keyword,
                contentType: "application/json",
                type: "get",
                onsuccess: function (root) {
                    self.modelToLoadUsage(root, keyword);
                }
            });
        },

        vinToLoadUsage: function (root, keyword) {
            var self = this;

            if (root.result.data === false) {
                alert("‘" + keyword + "’, " + language['10270']);
                return;
            }

            window.open(vinLoadUsageUrl + keyword, "_self");
        },

        modelToLoadUsage: function (root, keyword) {
            var self = this;

            if (root.result.data === false) {
                alert("‘" + keyword + "’, " + language['10271']);
                return;
            }

            window.open(modelLoadUsageUrl + keyword, "_self");
        },

        doAdvancedSearch: function (params) {
            var self = this;

            if (typeof self.opts.callbacks.onAdvancedSearch === "function") {
                self.opts.callbacks.onAdvancedSearch.apply(null, [params]);
            }
        }
    };

    return Search;
});