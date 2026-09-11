define(["grid", "settings", "ajax", "blockUI"], function (Grid, settings, ajax) {
    var language = settings.i18n;
    var defaultOpts = {
        manualDialog: "manual-dialog",
        manualClose: "manual-dialog-close"
    };

    var manualTypeCodeUrl = settings.actions.manualTypeCodeUrl;
    var loadProductListUrl = settings.actions.loadProductListUrl,
        ALL_OPTION = { value: "", text: language['10194'] };

    var Manual = function (options) {
        this.opts = $.extend(true, defaultOpts, options || {});

        this.init();
    };

    Manual.prototype = {

        init: function () {
            var self = this;

            self.buildDomEls();
            self.loadData();
            self.bindEvent();
            self.initComponent();
        },

        buildDomEls: function () {
            var self = this;

            self.$manualDialog = $("#" + self.opts.manualDialog);
            self.$manualClose = $("#" + self.opts.manualClose);
            self.$product = $("#mn-product-code");
            self.$machine = $("#mn-machine-code");
            self.$submachine = $("#mn-submachine-code");
        },

        initComponent: function () {
            var self = this;

            self.grid = new Grid({
                grid: {
                    gridId: "manual-search-grid",
                    fixedId: "manual-fixed-grid"
                },
                paging: {
                    id: "manual-paging"
                },
                filter: {
                    id: "manual-filter",
                    resetId: "manual-btn-clear",
                    filterId: "manual-btn-filter"
                },
                callbacks: {
                    onCleared: function () {
                        self.resetAllOption();
                    },
                    onLoadDataBefore:function () {
                    	$.loadingShow(self.$manualDialog);
                    },
                    onLoadDataAfter: function () {
                    	$.loadingHide(self.$manualDialog);
                    }
                }
            });

        },

        bindEvent: function () {
            var self = this;

            self.$manualClose.on("click", function () {
                self.close();
            });

        },

        buildData: function (data) {
            var self = this;

            data.products.splice(0, 0, ALL_OPTION);

            for (var key1 in data.machines) {
                data.machines[key1].splice(0, 0, ALL_OPTION);
            }
            for (var key2 in data.submachines) {
                data.submachines[key2].splice(0, 0, ALL_OPTION);
            }
            self.buildSelectOption(data);
        },

        loadData: function () {
            var self = this;

            ajax.invoke({
                url: loadProductListUrl,
                type: "GET",
                onsuccess: function (root) {
                    self.buildData(root.result.data);
                }
            });
        },

        buildSelectOption: function (data) {
            var self = this,
                rule = { "code": "value", "name": "text" },
                products = $.mappingJSON(data.products, rule, []);

            self.$product
                .bindSelectOption(products);

            self.$product.building({
                el: self.$machine,
                data: data.machines,
                text: "name",
                value: "code",
                changed: $.proxy(self.productChanged, self)
            });

            self.$machine.building({
                el: self.$submachine,
                data: data.submachines,
                text: "name",
                value: "code"
            });

            self.resetAllOption();
        },

        productChanged: function (val) {
            var self = this;

            self.resetOption(self.$submachine);

            if ($.trim(val).length === 0)
                self.resetOption(self.$machine);
        },

        open: function (params) {
            var self = this,
                dialogHeight = self.$manualDialog.height(),
                dialogWidth = self.$manualDialog.width();

            $(document).on("keyup.manual", function (e) {
                if (e.keyCode === 27) self.close();
            });

            $.blockUI({
                message: self.$manualDialog,
                css: {   
                	top: ($(window).height() - dialogHeight) / 2 + 'px',
                    left: ($(window).width() - dialogWidth) / 2 + 'px',
                    height: dialogHeight + 'px',
                    cursor: 'auto',
                    border: "0",
                    borderRadius: "4px"
                }
            });

            self.grid.filter();

            $.ajax({
                type: "POST",
                url: manualTypeCodeUrl,
                dataType: "json",
                success: function (data) {
                    if (data.success) {
                        var html = '<option value="">' + language['10194'] + '</option>';
                        for (var i = 0; i < data.result.data.length; i++) {
                            var obj = data.result.data[i];
                            html += '<option value="' + obj.code + '">' + obj.name + '</option>';
                        }
                        $('#mn-type-code').html(html);
                    }
                }
            });
        },

        close: function () {
            var self = this;

            $.unblockUI();
            self.resetAllOption();
        },

        resetAllOption: function () {
            var self = this;

            self.$product
                .find("option[value='']")
                .prop("selected", true);

            self.resetOption(self.$machine);

            self.resetOption(self.$submachine);
        },

        resetOption: function ($select) {
            var self = this;

            $select.find("option")
                .remove();

            $("<option/>").appendTo($select)
                .prop({ "text": ALL_OPTION.text, "value": ALL_OPTION.value });

            $select.get(0).selectedIndex = 0;
        }
    };

    return Manual;
});
