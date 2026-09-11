﻿define(["settings", "ajax", "mustache", "blockUI", "jqExtend", "jquery", "linq", "amplify"],
    function(settings, ajax, Mustache) {
		var seachPartsUrl = settings.actions.seachPartsUrl;
        var defaultOpts = {
            contentId: "group-content",
            templateId: "group-template",
            isGroupAllCollapse: false,
            isFirstUlExpand: settings.context.notSelect,
            callbacks: {
                onSelectionNode: null,
                onRenderDataAfter: null
            }
        },
            path = settings.context.host;

        var Group = function(options) {

            this.opts = $.extend({}, defaultOpts, options || {});

            this.isGroupAllCollapse = this.opts.isGroupAllCollapse;
            this.isFirstUlExpand = this.opts.isFirstUlExpand;

            this.init();
        };

        Group.prototype = {

            init: function() {
                var self = this;

                self.buildDomEls();
                self.buildTemplate();
                self.bindEvent();
                self.loadData();
            },

            buildDomEls: function() {
                var self = this;

                self.$groupContent = $("#" + self.opts.contentId);
                self.$groupTemplate = $("#" + self.opts.templateId);
            },

            buildTemplate: function() {
                var self = this;

                self.template = self.$groupTemplate.html();
            },

            bindEvent: function() {
                var self = this;

                self.$groupContent.on("click", "a[data-id]", function(e) {  
                    self.clickNode($(this), $(e.target).prop("tagName"));
                });
                $(document).keypress(function(e) {  
                    if(e.which == 13) {  
                    	$("#seachLi").click();
                    }  
                }); 
                $("#seachLi").on("click",function(e){
                	var partNo = $.trim($("#partNo").val().toUpperCase());
                	if(partNo==""){
                		return false;
                	}
                	//将隐藏的所有节点显示
                	$("#group-content").find("li").css("display","block");
                	//去除所有菜单颜色
        	  		$("#group-content").find("a").removeClass("orange-color");
        	  		//收起所有树节点
        	  		$("#group-content").find("li[data-level=1]").find("ul").css("display","none");
        	  		//还原所有树图标
        	  		$("#group-content").find("span").removeClass("group-content-expand-active");
        			//9L181097    11M0001
        			var tli =  $("#search-type").find("li[class=search-selected]")[0];
        			var codeType = $(tli).attr("data-action");
        			self.loadingShow();
        			$.ajax({
        	 		  	type: "POST",
        	 		  	url: seachPartsUrl,
        	 		  	data:{
        	 		  			code : $.trim($("#search-box").val()),
        	 		  			partCode : partNo,
        	 		  			codeType : codeType
        	 		  		}, 
        	 		  	success: function(e){
        	 		  		if(e.result.data.length<1){
        	 		  			self.OpenNode($.trim($("#partNo").val().toUpperCase()),false);
        	 		  		}else{
        	 		  			$.each(e.result.data,function(i,n){
        	 		  				self.OpenNode(e.result.data[i].legendCode,true);
        		 		  		});
        	 		  		}
        	 		  	},
        	 		  	complete:function(){
        	 		  		self.loadingHide();
        	 		  	}
        	  		});
                });
                
                $("#model_package").on("click",function(e){
                	var modelCode = settings.context.modelCode;
                	var url=settings.context.homePath+"usage/model-pack?modelCode="+modelCode;
                	window.open(url,'_blank');
                	
                });
            },

            loadData: function() {
                var self = this;

                self.loadingShow();
                ajax.invoke({
                    url: self.opts.loadGroupUrl,
                    data: self.opts.params,
                    onsuccess: function(root) {
                        self.loadingHide();
                        self.buildData(root);
                        self.handleData(self.data);
                        self.render(self.data);
                    },
                    onfailed: function() {
                        self.loadingHide();
                    }
                });
            },

            loadingShow: function() {
                $.blockUI({
                    message: "<h1><img src=" + path + "/css/images/busy.gif /> Please wait...</h1>"
                });
            },

            loadingHide: function() {
                $.unblockUI({
                    message: "<h1><img src=" + path + "/css/images/busy.gif /> Please wait...</h1>"
                });
            },

            buildData: function(root) {
                var self = this;
                
                self.data = root.result.data || [];
            },

            clickNode: function($node, tagName, node) {
                var self = this, num = 0,
                sole = $node.attr("data-sole"),
                    leaf = $node.attr("data-leaf"),
                    level = $node.closest("li").attr("data-level"),
                    systemCode = $node.attr("data-systemcode"),
                    systemText = self.$groupContent.find("a[data-systemcode='" + systemCode + "']:first b").text() || "",
                    nodes = self.getNodesById(sole);
                           
                if(tagName === "SELECT") {
                	nodes[0].legendCode = node.legendCode;
                }
                
                if (nodes.length > 0) {
                	nodes[0]["systemText"] = systemText;
                	if(tagName !== "SELECT") nodes[0]["legendCode"] = $node.attr("data-code");
                    self.clearNodesStatus();
                    if(tagName === "SPAN") {
                    	self.shrinkEl($node, leaf, tagName);
                    }else{
                		self.selectionNode(nodes, level, tagName, $node);
                    }
                }
                $node.removeClass("default-color").addClass("orange-color");
            },
            
            shrinkEl: function($node, leaf, tagName) {
            	var self = this;            	
            	
            	if ($node.next("ul").is(":visible")) {
                    self.collapse($node);
                } else if (leaf === "false") {
                    self.expand($node);
                }
            },

            clearNodesStatus: function() {
                var self = this;

                self.$groupContent
                    .find("a[data-id]")
                    .removeClass("orange-color")
                    .addClass("default-color");
            },

            selectionNode: function(nodes, level, tagName, $node) {
                var self = this,
                    callbacks = self.opts.callbacks,
                    node = nodes[0] || {};

                if (typeof callbacks.onSelectionNode === "function") {
                    callbacks.onSelectionNode.apply(self, [node, tagName, $node]);
                }
            },

            expand: function($node) {
                var self = this;

                $node.find("span:first")
                    .addClass("group-content-expand-active");
                $node.next("ul").slideDown(100);
            },

            collapse: function($node) {
                var self = this;

                $node.find("span:first")
                    .removeClass("group-content-expand-active");

                $node.next("ul").slideUp(100);
            },

            collapseSiblingNodes: function($node) {
                var self = this,
                    $siblingNodes = $node.parent("li").siblings();

                $siblingNodes.find("ul")
                    .hide();
                $siblingNodes.find("a span[data-area]")
                    .removeClass("group-content-expand-active");
            },
            
            handleData:function(data){
            	var me = this;
            	
            	for(var i = 0; i < data.length; i++){
            		if(data[i].legendCode == null) data[i].legendCode = "";
            		data[i].sole = Math.random() - 0.000001;
            		data[i].versions= JSON.stringify(data[i].versions);            		
            		if(data[i].children && data[i].children.length > 0) me.handleData(data[i].children);
            	}
            },

            render: function(data) {
                var self = this;
                    data = {
                        children: data
                    },
                    subTemplate = {
                        "subTemplate": self.template
                    },
                    output = Mustache.render(self.template, data, subTemplate);

                self.$groupContent.html(output);

                self.groupAllCollapse();

                if (!self.isFirstUlExpand && self.validateUrl()) {
                    self.firstUlExpand();
                }

                if (typeof self.opts.callbacks.onRenderDataAfter === "function") {
                    self.opts.callbacks.onRenderDataAfter.apply(self, []);
                }
            },

            validateUrl: function() {
                var self = this,
                	code = "legend";

                if (window.location.href.indexOf(code) >= 0) {
                    return false;
                } else {
                    return true;
                }

            },

            firstUlExpand: function() {
                var self = this;
                var $Lv1 = self.$groupContent.children("ul").find("li:first");
                self.firstExpand($Lv1);
            },


            firstExpand: function($li) {
                var self = this,
                    $node = $li.find("a:first");
                if (!$node.size() > 0) return;
                self.clickNode($node);
                self.firstExpand($li.children("ul").find("li:first"));
            },


            groupAllCollapse: function() {
                var self = this,
                    $nodes = self.$groupContent.find("li ul");

                if (self.isGroupAllCollapse) {
                    $nodes.show();
                } else {
                    $nodes.hide();
                }
            },

            getNodesById: function(sole) {
                var self = this,
                    data = {
                        children: self.data
                    };

                return Enumerable.Return(data)
                    .CascadeBreadthFirst("$.children", "")
                    .Where('$.sole == "' + sole + '"')
                    .ToArray();
            },

            checkedNode: function(params) {
                var self = this,
                    top = self.$groupContent.find("li[data-systemCode='" + params.systemCode + "']"),
                    level1 = top.find("a:first"),
                    //level3 = top.first().find("li[data-id='" + params.code + "']:first").find("a[data-code='" + params.legendCode + "']:first");
                    level3 = top.first().find("li[data-id='" + params.code + "']:first").find("a:first");
                	self.clickNode(level1);
                
                if (level3.length > 0) {
                    self.clickNode(level3);
                    level3.parents("li").find("span:first").addClass("group-content-expand-active");
                    level3.find("span:first").removeClass("group-content-expand-active");
                    level3.parents("ul").show();
                    top.show();
                }
            },
            OpenNode: function(nodeID,isCnode){
            	var nid = nodeID.split('_')[0];
    	  		var arr;
    	  		if(isCnode){
    	  			arr =$("#group-content").find("a[data-code *="+nid+"]");
    	  		}else{
    	  			arr = $("a:contains('"+nodeID+"')");
    	  		}
    			$.each(arr,function(i,n){
    				var t = arr[i];
					var level =$(t).parent().attr("data-level");
					var d= t;
					for(var j=1;j<level;j++){
						//多一层多2个父元素
						d = $(d).parent().parent();
						//alert($(d).text());
						$(d).css("display","block");
					}
					//模拟点击
					//$(t).click();
					//改变菜单颜色
					$(t).addClass("orange-color");
					//如果该节点下还有子节点就展开自身，并将符合搜索条件的子节点点亮
					var pno = $.trim($("#partNo").val());
					if($(t).parent().find("a[data-id *="+pno+"]").length>0){
						var self = $(t).parent().find("ul").eq(0);
						$(self).css("display","block");
						$(self).find("a[data-id *="+pno+"]").addClass("orange-color");
					}
    		  	})
    	  	}
        };

        return Group;
    });