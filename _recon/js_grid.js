define(["ajax",
        "mustache",
        "settings",
        "export",
        "json2",
        "linq",
        "jqExtend",
        "jqueryUI",
        "jqueryDatepickeri18n"
    ],
    function(ajax, Mustache, settings, Export) {

        var readUrl = settings.actions.readUrl,
            hostUrl = settings.context.host,
        	newReadUrl = settings.actions.newReadUrl;
        
        var defaultOpts = {
            common: {
                isExtendExport: true,
                isExtendLoading: true,
                isExtendValidation: true
            },
            filter: {
                id: "filter",
                resetId: "btn-reset",
                filterId: "btn-filter",
                extraCondition: []
            },
            grid: {
                gridId: "grid",
                fixedId: "fixed",
                keys: ["id"],
                params: {}
            },
            paging: {
                id: "paging",
                pageSize: 10,
                gotoPageId: "btnGoTo",
                topPageId: "btnTopPage",
                prevPageId: "btnPrevPage",
                nextPageId: "btnNextPage",
                bottomPageId: "btnBottomPage",
                pageCountId: "spPageCount",
                recordCountId: "spRecordCount",
                currentPageId: "tbCurrentPageIndex"
            },
            exports: {
                exportButtonId: "btnExport",
                exportFormWrapId: "crud-main-wrap"
            },
            ajax: {
                type: "POST",
                contentType: "application/json"
            },
            callbacks: {
                onRowClicked: null,
                onCleared: null,
                onLoadDataBefore: null,
                onModifyData: null,
                onSearchBefore: null,
                onSearchBeforePrevent: null,
                onLoadDataAfter: null
            }
        };

        var Grid = function(options) {
            this.opts = $.extend(true, {}, defaultOpts, options || {});

            this.currentIndex = 1;
            this.pageSize = this.opts.paging.pageSize;

            this.init();
        };

        Grid.prototype = {

            init: function() {
                var self = this;

                self.buildDomEls();
                self.buildTemplate();
                self.buildUrl();
                self.bindEvent();
                self.bindExport();
            },

            buildDomEls: function() {
                var self = this,
                    grid = self.opts.grid,
                    paging = self.opts.paging,
                    filter = self.opts.filter;

                self.$grid = $("#" + grid.gridId);
                self.$fixed = $("#" + grid.fixedId);

                self.$filter = $("#" + filter.id);
                self.$btnFilter = $("#" + filter.filterId);
                self.$btnReset = $("#" + filter.resetId);

                self.$paging = $("#" + paging.id);
                self.$pageCount = self.$paging.find("[data-id='" + paging.pageCountId + "']");
                self.$recordCount = self.$paging.find("[data-id='" + paging.recordCountId + "']");
                self.$currentPage = self.$paging.find("[data-id='" + paging.currentPageId + "']");
                self.$topPage = self.$paging.find("[data-id='" + paging.topPageId + "']");
                self.$prevPage = self.$paging.find("[data-id='" + paging.prevPageId + "']");
                self.$nextPage = self.$paging.find("[data-id='" + paging.nextPageId + "']");
                self.$bottomPage = self.$paging.find("[data-id='" + paging.bottomPageId + "']");
                self.$gotoPage = self.$paging.find("[data-id='" + paging.gotoPageId + "']");


            },

            buildTemplate: function() {
                var self = this;

                self.gridTemplate = self.$grid.find("script[type='text/template']").html();
                self.fixedTemplate = self.$fixed.find("script[type='text/template']").html();
            },

            buildUrl: function() {
                var self = this;

                self.readUrl = self.$grid.attr("data-read-url");
            },

            bindEvent: function() {
                var self = this;

                self.bindFilterEvent();
                self.bindGridEvent();
                self.bindPagingEvent();
            },

            bindExport: function() {
                var self = this;

                // extend export method
                if (self.opts.common.isExtendExport) {
                    if ($("#" + self.opts.exports.exportButtonId).size() == 1 && $("#" + self.opts.exports.exportFormWrapId).size() == 1) {
                    	Export.extend(self, {
                            exportButtonId: self.opts.exports.exportButtonId,
                            exportFormWrapId: self.opts.exports.exportFormWrapId
                        });
                    }

                }

            },

            bindFilterEvent: function() {
                var self = this,
                    df;

                self.$btnFilter.on("click", function(e) {
                    if (self.validateSearchBefore()) {
                    	//判断是否图例编码或者配件编码条件搜索，弹出新层
                    	$advancedSearchDialog = $("#advanced-search-dialog");
                    	var legendCode = $advancedSearchDialog.find("[data-field='legendCode']").val();
                    	var partNO = $advancedSearchDialog.find("[data-field='partNO']").val();
                    	
                    	var modelCode = $advancedSearchDialog.find("[data-field='modelCode']").val();
                    	var parentPartName = $advancedSearchDialog.find("[data-field='parentPartName']").val();
                    	var partName = $advancedSearchDialog.find("[data-field='partName']").val();
                    	var partNote = $advancedSearchDialog.find("[data-field='partNote']").val();
                    	var productCode = $advancedSearchDialog.find("[data-field='productCode']").val();
                    	var machineCode = $advancedSearchDialog.find("[data-field='machineCode']").val();
                    	var submachineCode = $advancedSearchDialog.find("[data-field='submachineCode']").val();
                    	var partCategoryCode = $advancedSearchDialog.find("[data-field='partCategoryCode']").val();
                    	var systemCode = $advancedSearchDialog.find("[data-field='systemCode']").val();
                    	if((legendCode!="" || partNO!="") 
                    			&& modelCode==""
                    			&& parentPartName==""
                    			&& partName==""
                    			&& partNote==""
                    			&& productCode==""
                    			&& machineCode==""
                    			&& submachineCode==""
                    			&& partCategoryCode==""
                    			&& systemCode==""){
                    		$("#new-search-dialog").show();
                    		$.ajax({
                	 		  	type: "POST",
                	 		  	url: newReadUrl,
                	 		  	data:{
                	 		  		legendCode:legendCode,
                        			partNO:partNO
                	 		  		},
                	 		  	success: function(e){
                	 		  		$("#new-search-grid tbody").html(e);
                	 		  	}
                	  		});
                    	}else{
                    		self.filter(e);
                    	}
                    }
                });

                self.$btnReset.on("click", function() {
                    self.clear();
                });

                self.$filter.on("keyup", "input[type='text'][data-field]", function(e) {
                    if (e.keyCode === 13 && self.validateSearchBefore()) self.filter();
                });

                self.$filter.find("input[data-dateformat]").each(function(index, el) {
                    df = $(el).attr("data-dateformat");
                    $(el).datepicker({
                        dateFormat: df,
                        showOn: "button",
                        buttonImage: hostUrl + "/css/images/datepicker_btn_img.png"
                    });
                });
            },

            bindGridEvent: function() {
                var self = this,
                    sender, action;

                self.$fixed.on("click", "tbody > tr", function(e) {
                    sender = e.target;
                    action = $(sender).attr("data-action");
                    self.rowClick(sender, e, action);
                    e.stopPropagation();
                });

                self.$grid.on("click", "tbody > tr", function(e) {
                    sender = e.target;
                    action = $(sender).attr("data-action");
                    self.rowClick(sender, e, action);
                    e.stopPropagation();
                });
                
            },

            rowClick: function(sender, e, action) {
                var self = this,
                    rowIndex = $(sender).closest("tr").index(),
                    keys = self.getRowKeys(rowIndex),
                    cells = keys ? self.getRowValues(keys) : {};

                if (self.opts.callbacks.onRowClicked)
                    self.opts.callbacks.onRowClicked.apply(self, [e, cells, keys, action]);
            },

            getRowValues: function(params) {
                var self = this,
                    rowValues, condition = [],
                    keys = JSON.parse($.escapeSpecialChars(params));

                for (var key in keys) {
                    if ($.inArray(key, self.opts.grid.keys) > -1)
                        condition.push(" ($." + key + "=='" + keys[key] + "') ");
                }

                rowValues = Enumerable.From(self.data)
                    .Where(condition.join("&&"))
                    .Select(self.getDataKeys(self.data))
                    .ToArray();

                for (var i = 0, values; values = rowValues[i]; i++) {
                    for (var key in values) {
                        rowValues[i][key] = typeof values[key] !== "undefined" ? values[key] : "";
                    }
                }

                return rowValues[0] ? rowValues[0] : {};
            },

            getDataKeys: function(data) {
                var self = this,
                    keys = [];

                if (data.length > 0) {
                    for (var key in data[0]) {
                        keys.push(key + ": $." + key);
                    }
                }

                return "{" + keys.join(",") + "}";
            },

            getRowKeys: function(rowIndex) {
                var self = this,
                    keys = self.$grid.find("tbody > tr:eq(" + rowIndex + ")").attr("data-keys");

                return keys;
            },

            bindPagingEvent: function() {
                var self = this,
                    action, $target;

                self.$paging.on("click", "li[class*='-enabled'] > a", function(e) {
                    action = $(this).attr("data-action");
                    switch (action) {
                        case "top":
                            if (self.pageCount > 1)
                                self.currentIndex = 1;
                            break;
                        case "prev":
                            if (self.currentIndex > 1)
                                self.currentIndex--;
                            break;
                        case "next":
                            if (self.currentIndex < self.pageCount)
                                self.currentIndex++;
                            break;
                        case "bottom":
                            if (self.pageCount > 1 && self.currentIndex != self.pageCount)
                                self.currentIndex = self.pageCount;
                            break;
                        default:
                            break;
                    }
                    self.loadData();
                });

                self.$currentPage.on("keyup", function(e) {
                    if (e.keyCode === 13 && self.validateSearchBefore()) self.gotoPage();
                });

                self.$gotoPage.on("click", function(e) {
                    if (self.validateSearchBefore()) self.gotoPage();
                });
            },

            validateSearchBefore: function() {
                var self = this;
                if (typeof self.opts.callbacks.onSearchBeforePrevent === "function") {
                    var flag = self.opts.callbacks.onSearchBeforePrevent.apply(self, [self.getParams()]);
                    return flag;
                }
                return true;
            },

            filter: function(e) {
                var self = this;

                if (typeof self.opts.callbacks.onSearchBefore === "function") {
                    self.opts.callbacks.onSearchBefore.apply(self, []);
                }

                self.sort = {};
                self.currentIndex = 1;
                self.loadData(e);
            },

            loadData: function(e) {
                var self = this,
                    params, finallyParams,newParams,
                    ajaxConfig = self.opts.ajax,
                    callbacks = self.opts.callbacks,
                    params = self.getParams();

                if (typeof callbacks.onLoadDataBefore === "function")
                    callbacks.onLoadDataBefore.apply(self, [params]);

                // shopping cart change current shopping cart load data,but filters only has current shopping cart code
                if (typeof callbacks.onModifyData === "function"){
                	newParams = callbacks.onModifyData.apply(self, []);
                	params = JSON.parse(params);
                	if($.trim(newParams.value).length === 0) newParams.value = "";
                	if(!e || $(e.target).prop("tagName") !== "SELECT"){
            			params.filters.push(newParams);
                	}else if(e && $(e.target).prop("tagName") === "SELECT"){
                		params.filters = [];
                		params.filters.push(newParams);
                	}
                	params = JSON.stringify(params);
                }

                self.xhr = ajax.invoke({
                    contentType: ajaxConfig.contentType,
                    type: ajaxConfig.type,
                    url: self.readUrl,
                    data: params,
                    onsuccess: $.proxy(self.buildData, self),
                    onfailed: $.proxy(self.failed, self)
                });
            },

            getParams: function() {
                var self = this,
                    grid = self.opts.grid;

                if ($.isEmptyObject(grid.params)) {
                    return JSON.stringify({
                        filters: self.getCondition(),
                        sorts: [],
                        page: self.currentIndex || 1,
                        limit: self.pageSize || 10
                    });
                } else {
                    return grid.params;
                }
            },

            buildData: function(root) {
                var self = this,
                    i, renderData,
                    pageSize = self.opts.paging.pageSize,
                    callbacks = self.opts.callbacks;

                self.data = root.result.data || [];
                self.recordCount = root.result.total || 0;
                self.pageCount = (self.recordCount % pageSize == 0) ? (parseInt(self.recordCount / pageSize)) : (parseInt(self.recordCount / pageSize) + 1);

                for (i = 0; i < self.data.length; i++) {
                    self.data[i]["rowNumber"] = parseInt(self.currentIndex - 1) * parseInt(self.pageSize) + (i + 1);
                }

                if (typeof callbacks.onLoadDataAfter === "function")
                    callbacks.onLoadDataAfter.apply(self, [self.data, root]);

                self.render(self.data);
                self.pagingtionStatus();
            },

            getCondition: function() {
                var self = this,
                    field, value,
                    operator, condition = [],
                    $item = self.$filter.find("[data-scope='filter']"),
                    extraCondition = self.opts.filter.extraCondition;

                $(extraCondition).each(function(index, item) {
                    field = item.field;
                    value = item.value;
                    fieldType = item.fieldType || "S";
                    operator = item.operator || "EQ";
                    if ($.trim(value).length > 0)
                        condition.push({
                            property: field,
                            value: value,
                            operation: operator
                        });
                });

                $item.each(function() {
                    field = $(this).attr("data-field");
                    value = $(this).getVal();
                    fieldType = ($(this).attr("data-fieldType") || "S");
                    operator = ($(this).attr("data-operator") || "EQ");
                    if ($.trim(value).length > 0)
                        condition.push({
                            property: field,
                            value: value,
                            operation: operator,
                            fieldType: fieldType
                        });
                });

                return condition;
            },

            // get export header
            getExportSheet: function() {
                var self = this,
                    columns = [],
                    sheetname = self.$export.attr("data-export-filename"),
                    $ths = self.$grid.find("th[data-field]");

                $ths.each(function(index, item) {
                    columns.push({
                        Title: $(item).text(),
                        Field: $(item).attr("data-field")
                    });
                });

                return [{
                    SheetName: sheetname,
                    Columns: columns
                }];
            },

            clear: function() {
                var self = this,
                    selector = "[data-scope='filter'][data-isclear!='false']",
                    $clearItems = self.$filter.find(selector);

                $clearItems.each(function() {
                    $(this).clearVal();
                });

                if (typeof self.opts.callbacks.onCleared === "function")
                    self.opts.callbacks.onCleared.apply(this, []);
            },

            pagingtionStatus: function() {
                var self = this;

                self.$pageCount.html(self.pageCount);
                self.$recordCount.html(self.recordCount);
                self.$currentPage.val(self.currentIndex);
                self.pagingButttonStatus();
            },

            gotoPage: function() {
                var self = this,
                    gotoPageIndex = self.$currentPage.val();

                if (!/^[0-9]+$/.test(gotoPageIndex)) {
                    gotoPageIndex = 1;
                }
                if (parseInt(gotoPageIndex) > self.pageCount) {
                    self.currentIndex = 1;
                } else {
                    self.currentIndex = parseInt(gotoPageIndex);
                }

                self.loadData();
            },

            pagingButttonStatus: function() {
                var self = this;

                self.$topPage.removeClass("common-paging-top-enabled").addClass("common-paging-top-disabled");
                self.$prevPage.removeClass("common-paging-prev-enabled").addClass("common-paging-prev-disabled");
                self.$nextPage.removeClass("common-paging-next-enabled").addClass("common-paging-next-disabled");
                self.$bottomPage.removeClass("common-paging-bottom-enabled").addClass("common-paging-bottom-disabled");

                if (self.currentIndex > 1 && self.currentIndex < self.pageCount) {
                    self.$topPage.addClass("common-paging-top-enabled");
                    self.$prevPage.addClass("common-paging-prev-enabled");
                    self.$nextPage.addClass("common-paging-next-enabled");
                    self.$bottomPage.addClass("common-paging-bottom-enabled");
                } else if (self.currentIndex === 1 && self.pageCount > 1) {
                    self.$nextPage.addClass("common-paging-next-enabled");
                    self.$bottomPage.addClass("common-paging-bottom-enabled");
                } else if (self.pageCount === self.currentIndex && self.currentIndex > 1) {
                    self.$topPage.addClass("common-paging-top-enabled");
                    self.$prevPage.addClass("common-paging-prev-enabled");
                }
            },

            render: function(data) {
                var self = this,
                    gridHtml, fixedHtml,
                    $renderGrid = self.$grid.find("tbody"),
                    $renderFixed = self.$fixed.find("tbody");

                gridHtml = Mustache.to_html(self.gridTemplate, {
                    records: data
                });

                $renderGrid.html(gridHtml).show();

                if (self.fixedTemplate) {
                    fixedHtml = Mustache.to_html(self.fixedTemplate, {
                        records: data
                    });
                    $renderFixed.html(fixedHtml).show();
                }

                self.gridOddStyle();
            },

            gridOddStyle: function () {
                var self = this,
                    $gridBody = self.$grid.find("tbody"),
                    $fixedGridBody = self.$fixed.find("tbody");

                $gridBody.find("tr:odd").addClass("odd");
                $fixedGridBody.find("tr:odd").addClass("odd");
            }
        };

        return Grid;
    });