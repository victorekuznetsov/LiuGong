﻿define(["grid", "settings", "mustache", "orderQty", "ajax", "jqueryScrollIntoView", "blockUI", "amplify"], function(Grid, settings, Mustache, OrderQty, ajax) {
    var language = settings.i18n,
    	path = settings.context.host,
    	shoppingCartSaveListUrl = settings.actions.shoppingCartSaveListUrl,
    	partUnSaleSaveUrl=settings.actions.partUnSaleSaveUrl|| "";
    var loadPartsUrl = settings.actions.loadPartsUrl || "",
        remarkUrl = settings.actions.remarkUrl || "",
        crumbsData = JSON.parse(settings.context.crumbs || "[]"),
        usageCondition = JSON.parse(settings.context.usageCondition || "[]");

    var defaultOpts = {
    		partsId: ("parts"),
	        partsContentId: ("parts-content"),
	        partsTemplateId: ("parts-template"),
	        remarkDialogId: ("user-remark-dialog"),
	        remarkContentId: ("remark-content"),
	        shoppingDialogId: ("shopping-dialog"),
	        callbacks: {}
    	};

    var Parts = function(options) {
        this.opts = $.extend(true, defaultOpts, options || {});
        this.init();
    };

    Parts.prototype = {

        init: function() {
            var self = this;

            self.buildDomEls();
            self.buildTemplate();
            self.bindEvent();
        },

        buildDomEls: function() {
            var self = this;

            self.remarkBtnActive=true;
            self.$parts = $("#" + this.opts.partsId);
            self.$partsContent = $("#" + this.opts.partsContentId);
            self.$partsTemplate = $("#" + this.opts.partsTemplateId);
            self.$remarkDialog = $("#" + this.opts.remarkDialogId);
            self.$remarkContent = $("#" + this.opts.remarkContentId);
            self.$shoppingDialog = $("#" + this.opts.shoppingDialogId);
            self.$shoppingContent = self.$shoppingDialog.find("input[data-field='shopping-num-edit']");
        },

        buildTemplate: function() {
            var self = this;

            self.tempate = self.$partsContent.find("script").html();
        },

        bindEvent: function() {
            var self = this,
                action, partNO, mpq, partName;

            self.$partsContent.on("click", "tr", function(e) {
                self.selectionRow(e);
            });

            self.$partsContent.on("click", "a[data-action]", function(e) {
                action = $(this).attr("data-action");
                partNO = $(this).closest("tr").attr("data-partNO");
                mpq = $(this).closest("tr").attr("data-mpq");
                partName = $(this).closest("tr").attr("data-partName");
				preServed4= $(this).closest("tr").attr("data-preServed4");
				
                switch (action) {
                    case "reverse":
                        self.reverseView(partNO);
                        break;
                    case "remark":
                        self.remarkView(partNO);
                        self.$remarkDialog.data("$tr",$(this).closest("tr"));
                        break;
                    case "buy":
                    	if($(e.target).attr("data-order") === "true"){
                    		self.partBuy(partNO, mpq, partName,preServed4);
                    	}else{
                    		alert(language["10210"]);
                    	}
                        break;
                    case "part-un-sale"://wbw add 20230109
                    	self.partUnSaleSave(partNO,mpq);
                        break;
                    default:
                        break;
                }
            });
            self.$parts.on("click","a[attr=batchBuy]",function(){
            	var buyPartArr = new Array();
            	self.$partsContent.find('input[attr="child"]').each(function(i,n){
            		if($(this).is(':checked')){
            			var buyPart = new Object();
            			buyPart.partNO =$(this).attr("id");
            			buyPart.mpq = $(this).parent().parent().attr("data-mpq");
            			buyPart.submachineCode = crumbsData[2].code;
            			buyPart.qty = $(this).parent().parent().find("td").eq(3).text();
            			buyPart.preServed4 = $(this).parent().parent().attr("data-preServed4");
            			buyPartArr.push(buyPart);
            		}
            	});
            	self.batchBuy(buyPartArr);
            }),
            self.$remarkDialog.on("click", "a[data-action]", function(e) {
                action = $(e.target).attr("data-action");
                switch (action) {
                    case "confirm":
                        self.remarkConfirm(action);
                        break;
                    case "cancel":
                        self.closeDialog();
                        break;
                    default:
                        break;
                }
            });

            self.$shoppingDialog.on("click", "a[data-action]", function(e) {
                action = $(e.target).attr("data-action");
                switch (action) {
                    case "confirm":
                        self.shoppingConfirm(action);
                        break;
                    case "cancel":
                        self.closeDialog();
                        break;
                    default:
                        break;
                }
            });


            $("div[class='parts-content'][data-area='usage-content']").on("scroll",function(){
            	$("div[class='parts-head'][data-area='usage-head']").scrollLeft($(this).scrollLeft());
	            });

            },

        selectionRow: function(e) {
            var self = this,
                callout = $(e.target).closest("tr").attr("data-callout");

            self.changeRowBg(callout);

            if (typeof self.opts.callbacks.onSelectionRow === "function") {
                self.opts.callbacks.onSelectionRow.apply(null, [callout]);
            }
        },

        loadData: function(params) {
            var self = this;

            self.loadingShow();
            ajax.invoke({
                url: loadPartsUrl,
                data: params,
                onsuccess: function(root) {
                    self.buildData(root.result);
                    self.render(self.data);
                },
                onfailed: function(root) {
                    alert(language['10266'] + "：" + root.reason);
                    self.loadingHide();
                }
            });
        },

        buildData: function(result) {
            var self = this,
            	i = 0,
                data = result.data || [];

            self.data = data;
        },

        render: function(data) {
            var self = this,
                output = Mustache.render("{{#records}}" + self.tempate + "{{/records}}", {
                    records: data
                });

            self.$partsContent.html(output);

            self.checkPartNO(data);
            self.loadingHide();
        },

        loadingShow: function() {
            this.$parts.block({
                message: "<h1><img src=" + path + "/css/images/busy.gif /> Please wait...</h1>"
            });
        },

        loadingHide: function() {
            this.$parts.unblock({
                message: "<h1><img src=" + path + "/css/images/busy.gif /> Please wait...</h1>"
            });
        },

        checkPartNO: function(data) {
            var self = this,
                tr = self.$partsContent.find("tr");

            if (usageCondition.partNO) {
                for (var i = 0; i < data.length; i++) {
                    if (data[i].partNO === usageCondition.partNO) {
                        tr.eq(i).addClass("checked-tr");
                    }
                }
            }
        },

        reverseView: function(partNO) {
            var self = this;

            amplify.publish("open-advancedsearch", partNO);
        },

        remarkView: function(partNO, mpq) {
            var self = this;

            self.$remarkContent.val("");
            self.openDialog(self.$remarkDialog, partNO, mpq);
        },

        partBuy: function(partNO, mpq, partName,preServed4) {
            var self = this,
                params = {
                    partNO: partNO,
                    mpq: mpq,
                    submachineCode: crumbsData[2].code,
                    preServed4:preServed4
                };

            amplify.publish("open-order-qty", params);
        },
        batchBuy:function(buyPartArr){
        	var params = ""; 
        	var orderRemind="";//订购提醒
        	
        	if(buyPartArr.length==0)
        	{
        		//alert("buyPartArr.length="+buyPartArr.length);
        		alert(language['20033'] + "!");//请选择配件！
        		return;
        	}
        	for(var i=0;i<buyPartArr.length;i++){
        		params+=buyPartArr[i].partNO+","+buyPartArr[i].mpq+","+buyPartArr[i].submachineCode+","+buyPartArr[i].qty+";";
        		if(buyPartArr[i].preServed4!="")
        			orderRemind+=buyPartArr[i].partNO+language['20032']+":"+buyPartArr[i].preServed4+".\n";
        	}
        	if(orderRemind!="")
        		alert(orderRemind);
        	
        	//alert(params);
        	
        	$.ajax({
                url: shoppingCartSaveListUrl,
                type:"post",
                data: {listJsonData:params},
                dataType: "json",  
                success: function(root) {
                	amplify.publish("load-shopping-cart-count");
                	if(root.msg==null){
                		alert(language['10265'] + "!\n\n"+language['20042']);//增加提示 wbw 20200102
                	}else{
                		alert(root.msg);
                	}
                }
            });
        },
        remarkConfirm: function(action) {
            var self = this,
                partNO = self.$remarkDialog.find("a[data-partNO]").attr("data-partNO"),
                content = self.$remarkContent.val(),
                params = {
                    "partNO": partNO,
                    "content": content
                };

            if (self.remarkValidate()) {
                self.submit(remarkUrl, params, "remark");
            }
        },

        remarkValidate: function() {
            var self = this,
                valLength = $.trim(self.$remarkContent.val()).length;

            if (valLength > 400) {
                alert(language['10299']);
                return false;
            } else if (valLength == 0) {
                alert(language['10300']);
                return false;
            } else {
                return true;
            }
        },

        submit: function(url, params, action) {
            var self = this;

            if(!self.remarkBtnActive){
            	return;
            }
            ajax.invoke({
                url: url,
                data: params,
                onsuccess: function(root) {
                    if (action === "remark") {
                        alert(language['10244']);
                        self.closeDialog();
                        self.$remarkDialog.data("$tr").find("a[data-note='note']").removeClass().addClass("parts-tab-node-active");
                    } else if (action === "shopping" && root.result.success) {
                        alert(language['10244']);
                        self.closeDialog();
                    } else if (action === "shopping" && !root.result.success) {
                        alert(language['10266'] + "：" + root.msg);
                    }
                    self.remarkBtnActive=true;
                },
                onfailed: function(root) {
                    alert(language['10266'] + "：" + root.reason);
                }
            });
            self.remarkBtnActive=false;

        },

        openDialog: function(messageObj, partNO, mpq, partName) {
            var self = this,
                dialogHeight = messageObj.height(),
                dialogWidth = messageObj.width();

            messageObj.find("[data-action='confirm']")
                .attr("data-partNO", partNO)
                .attr("data-mpq", mpq)
                .attr("data-partName", partName);

            $.blockUI({
                message: messageObj,
	            css: {
	            	top: ($(window).height() - dialogHeight) / 2 + 'px',
	                left: ($(window).width() - dialogWidth) / 2 + 'px',
	                height: dialogHeight + 'px',
	                cursor: 'auto',
	                border: "0",
	                borderRadius: "4px"
	            }
            });
        },

        closeDialog: function() {
            var self = this;

            $.unblockUI();
        },

        linkPart: function(callout) {
            var self = this,
                $activeRows = self.$partsContent.find("tr[data-callout='" + callout + "']");

            $activeRows.scrollIntoView();
            self.changeRowBg(callout);
        },

        changeRowBg: function(callout) {
            var self = this,
                $trs = self.$partsContent.find("tr"),
                $activeRows = self.$partsContent.find("tr[data-callout='" + callout + "']");

            $trs.removeClass("checked-tr");
            $activeRows.addClass("checked-tr");
        },
        
        //不可销售零件保存 wbw 20230109 add 
        partUnSaleSave : function(partNO,mpq){
        	 var params = {
                     "partNo": partNO,
                     "qty": mpq
                 };
        	 
        	 $.ajax({
                 url: partUnSaleSaveUrl,
                 data: params,
                 type:"post",
                 success: function(root) {
                         alert(language['10244']);//保存成功
                 },
                 failed: function(root) {
                     alert(language['保存失败'] + "：" + root.reason);
                 }
             });
        }
    };

    return Parts;
});
