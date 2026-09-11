require(["settings",
        "group",
        "parts",
        "legend_new",//svg 20200103 wbw 
        //"legend",
        "layout",
        "amplify",
        "json2",
        "jquery",
        "domReady!",
        "layResizable"],
    function (settings, Group, Parts, Legend, Layout) {
        var vin = settings.context.vin,
            modelCode = settings.context.modelCode,
            crumbsData = JSON.parse(settings.context.crumbs || "[]"),
            usageCondition = JSON.parse(settings.context.usageCondition || "[]");

        var usage = {

            init: function () {
                var self = this;

                self.bindDomEls();
                self.settingHeight();
                self.initComponent();
                self.bindResizable();
            },

            bindDomEls: function () {
                var self = this;

                self.$head = $("#head");
                self.$crumbs = $("#crumbs-wrap");
                self.$mainContent = $("#usage-content-layResizable");
            },

            settingHeight: function () {
                var self = this,
                    windowHeight = $(window).height(),
                    headHeight = self.$head.height(),
                    crumbsHeight = self.$crumbs.height(),
                    usageHeadHeight = $("[data-area='usage-head']").height(),
                    finallyHeight = windowHeight - headHeight - crumbsHeight - usageHeadHeight - 15;

                self.changeHeight(finallyHeight);

                $(window).on("resize", function () {
                    windowHeight = $(window).height(),
                        finallyHeight = windowHeight - headHeight - crumbsHeight - usageHeadHeight - 15;
                    self.changeHeight(finallyHeight);
                });
            },

            changeHeight: function (finallyHeight) {
                var self = this;

                $("[data-area='usage-content']").css("height", finallyHeight);
                $("[data-area='usage-content-mask']").css("height", finallyHeight + 30);
            },

            initComponent: function () {
                var self = this, groupParams = self.getGroupParams();

                self.layout = new Layout({
                    onLayoutExpand: function () {
                        self.layResizable.resizeToAdjust();
                    }
                });

                self.group = new Group({
                    params: groupParams.params,
                    loadGroupUrl: groupParams.loadGroupUrl,
                    callbacks: {
                        onSelectionNode: $.proxy(self.selectionNode, self),
                        onRenderDataAfter: $.proxy(self.checkedGroupNode, self)
                    }
                });

                self.parts = new Parts({
                    callbacks: {
                        onSelectionRow: $.proxy(self.selectionPartsRow, self)
                    }
                });

            },

            selectionLegend: function (callout) {
                var self = this;

                self.parts.linkPart(callout);
            },

            selectionPartsRow: function (callout) {
                var self = this;

                self.legend.linkLegend(callout);
            },

            getGroupParams: function () {
                var self = this, params, loadGroupUrl;

                if ($.trim(vin).length > 0) {
                    params = {
                        vin: vin
                    };
                    loadGroupUrl = settings.actions.vinLoadGroupUrl;
                } else {
                    params = {
                        modelCode: modelCode
                    };
                    loadGroupUrl = settings.actions.modelLoadGroupUrl;
                }

                return {
                    params: params,
                    loadGroupUrl: loadGroupUrl
                };
            },

            selectionNode: function (node, tagName, $node) {
                var self = this, params = {
                    vin: vin,
                    modelCode: modelCode,
                    systemCode: node.systemCode || "",
                    legendCode: node.legendCode || "",
                    parentPartNo: node.parentPartNo || ""
                };
                
                if(!self.legend && params.legendCode){
                	 self.legend = new Legend({
                         callbacks: {
                             onSelectionLegend: $.proxy(self.selectionLegend, self),
                             onChange: function ($node, tagName, node) {
                             	self.group.clickNode($node, tagName, node);
                             }
                         }
                     });
                	 self.legend.initializeFlash(node);
                	 //svg 20200103 wbw 
                	 self.legend.initSvgCmp(node);
                	 
                }
               
                if(tagName !== "SPAN"){
	                if(node.legendCode.length > 0) self.loadCrumbs(node);
	                
	                if(node.level !== 1){
	                	if(params.legendCode) self.legend.changeLegendList(node, $node, tagName);
	                	if (node.legendCode !== null && node.legendCode.length > 0) self.parts.loadData(params);
		                //if (node.legendCode !== null) self.legend.loadLegend(node.legendCode);
	                	//svg wbw 20200103 
	                	if (node.legendCode) self.legend.loadLegendSvg(node.legendCode);
	                }
                }else if(tagName === "SPAN" && node.level === 1){
                	self.loadCrumbs(node);
                }
            },

            checkedGroupNode: function () {
                var self = this, params = {
                    vin: vin,
                    modelCode: modelCode,
                    systemCode: usageCondition.systemCode || "",
                    legendCode: usageCondition.legendCode || "",
                    code: usageCondition.code || "",
                    partNO: usageCondition.partNO || "",
                    callout: usageCondition.callout || ""
                };

                self.group.checkedNode(params);
            },

            loadCrumbs: function (node) {
                var self = this,
                	params = {},
                	systemParams = {
                             label: settings.i18n[10063],
                             text: node.systemText,
                             type: "systemCode",
                             code: node.systemCode,
                             sort: crumbsData.length + 1
                         };
                amplify.publish("crumbs-change", systemParams, node.systemCode);
                
                if (node.level > 1) {
                    params = {
                        label: settings.i18n[10251],
                        text: (node.legendCode || "") + "(" + node.text + ")",
                        type: "legendCode",
                        code: node.legendCode,
                        sort: crumbsData.length + 2
                    };
                    amplify.publish("crumbs-change", params, node.systemCode);
                }                
                
            },

            bindResizable: function () {
                var self = this,
                    left;

                self.$mainContent.layResizable({
                    lefts: [5, 15, 35],
                    // min:760,
                    onDragStop: function (params) {
                        left = parseInt(params.colRight.css("left")) - params.distance;
                        params.colRight.css("left", left);
                        self.layout.rememberElWidth();
                    },
                    onInitFinish: function () {
                        self.layResizable = this;
                    }
                });
            }
        };

        usage.init();
    });
