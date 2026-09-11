define(["settings", "ajax","svgOperator", "history", "swfobject","group" ],
    function (settings, ajax,svgOperator) {
        var expressInstallSwfurl = settings.hotpoint.playerSwfUrl,
            legendPath = settings.hotpoint.legendPath,
            hotpointSwfUrl = settings.hotpoint.hotpointSwfUrl,
            loadHotpointUrl = settings.actions.loadLegendHotpointUrl,
            legendFTPPath = settings.context.legendFTPPath,
            childNodeUrl = settings.actions.childNodeUrl,
            defaultOpts = {
        		callbacks: {
                	onChange: null
                }
        	};

        var language = settings.i18n;

        var Legend = function (options) {
            this.opts = $.extend(true, defaultOpts, options || {});

            this.init();
        };

        Legend.prototype = {

            init: function () {
                var self = this;

                self.bindDomEls();
                self.bindEvent();
            },

            bindDomEls: function () {
                var self = this;

                self.$legendList = $("#legend-list");
            },

            bindEvent: function () {
                var self = this;

                              
                self.$legendList.change(function(e){
                	if(typeof self.opts.callbacks.onChange === "function"){
                		self.node["legendCode"] = self.$legendList.find(":selected").attr("data-code");
                		self.opts.callbacks.onChange.apply(null, [self.$node, $(this).get(0).nodeName, self.node])
                	}
                	var legendCode = $("#legend-list option:selected").attr("data-code");
                	var nodeCode = $("#legend-list option:selected").attr("data-id");
                	var modelCode = $("#search-box").val();
                	var tli =  $("#search-type").find("li[class=search-selected]")[0];
        			var codeType = $(tli).attr("data-action");
                	$.ajax({
                        url: childNodeUrl,
                        type:"post",
                        data: {
                        	modelCode:modelCode,
                        	legendCode:legendCode,
                        	codeType:codeType
                        	}, 
                        success: function(root) {
                        	//新油品替换，套色问题，取消如下比较
//                        	var selectNode = $(group).find("li[data-id="+nodeCode+"]");
//                        	var level = selectNode.attr("data-level");
//                        	var i = parseInt(level) + 1;
//                        	var sn = selectNode.find("ul").find("li[data-level="+i+"]");
//                        	var str = root.split(',');
//                        	sn.each(function(){
//                        		var cn = $(this).attr("data-id");
//                        		cn = cn.split('_')[0];
//                        		var isExist = false;
//                        		for(var i=0;i<str.length;i++){
//                        			if(str[i]==cn){
//                        				isExist = true;
//                            			break;
//                            		}
//                        		}
//                        		if(isExist){
//                        			$(this).show();
//                        		}else{
//                        			$(this).hide();
//                        		}
//                        	})
                        }
                    });
                });
            },

            legendLinkPart: function (callout) {
                var self = this;

                if (typeof self.opts.callbacks.onSelectionLegend === "function") {
                    self.opts.callbacks.onSelectionLegend.apply(null, [ callout ]);
                }
            },

            loadLegend: function (legendCode) {
                var self = this,
                    url = legendPath + "?url=" + legendFTPPath + legendCode + ".swf";

                if(legendCode.length > 0)
                	self.render(url);
            },
            
            loadLegendSvg:function(legendCode){
            	var self=this,
            		svgurl=self.getLegendSvgUrl({legendCode:legendCode});
            	//alert("svgurl="+svgurl);
            	if(legendCode.length > 0){
            		 self.svgOperator.load(svgurl, function(error, svgObj) {
	                     if (error == null) {
	                         //console.log(svgObj);
	                     } else {
	                        // console.log('load error!');
	                     }
            		 });
            	}
            	
            },

            initializeFlash: function (data) {
                var self = this, params = {
                    quality: "high",
                    bgcolor: "#ffffff",
                    allowscriptaccess: "sameDomain",                    
                    allowfullscreen: "true",
                    wmode: "opaque"                    
                }, attributes = {
                    id: "hotpoint",
                    name: "hotpoint",
                    align: "middle"
                },
                existLegend = self.getExistLegend(data),
                url = self.getLegendUrl(data),
                config = {
                    assistiveTool: 1,
                    legend: url,
                    isExistLegend: existLegend,
                    needHotPoint: "true",
                    maxScale: "10",
                    minScale: "2",
                    deltaScale: "50"
                };
                
                swfobject.embedSWF(hotpointSwfUrl,
                    "flash-content",
                    "100%",
                    "100%",
                    "10.2.0",
                    expressInstallSwfurl,
                    config,
                    params,
                    attributes);
                
            },
            
            initSvgCmp:function(data){
            	var self=this,
            	 existLegend = self.getExistLegend(data),
                 url = self.getLegendSvgUrl(data);
            	//alert("initSvgCmp="+url);
            	self.svgOperator = new svgOperator({
                    //svg容器
                    $tag: $("#svg_operator"),
                    //工具条
                    $tools: $("#svg_tooltpl"),
                    //无图路径
                    nopic: settings.context.host+"/css/images/nopic.png",
                    //占位图路径
                    clearpic:settings.context.host+ "/css/images/none.png",
                    //初始svg
                    svgUrl: url,
                    //默认缩放
                    scale: 1,
                    //回调函数
                    callbacks: {
                        //点击热点
                        onSelectionText: function(callout) {
                        	 self.legendLinkPart(callout);
                        },

                        //SVG加载完成
                        onLoadComplete: function(svgObj) {

                        },

                        //点击工具条
                        onToolClick: function() {

                        },

                        //旋转
                        onRotate: function(degree) {

                        },

                        //复位
                        onReset: function() {

                        }
                    }
                });
            },

            getExistLegend:function(data){
                 return data.legend;
            },

            getLegendUrl:function(data){

              return legendPath + "?url=" + legendFTPPath + data.legendCode + ".swf";
            },
            
            getLegendSvgUrl:function(data){
            	var code = data.legendCode;//'00C5306_000_00';
            	//console.log(legendPath + "?url=" + settings.context.svgLegendFTPPath + code + ".svg");
            	return legendPath + "?url=" + settings.context.svgLegendFTPPath + code + ".svg";
            	//return legendPath + "?url=" + settings.context.svgLegendFTPPath + "00C5306_000_00" + ".svg";
            },

            render: function (url) {
                var self = this,
                    hotpoint = self.getMovie("hotpoint");

                if (typeof hotpoint === "undefined") {
                    alert(language["12285"]);
                    return;
                }
                if (typeof hotpoint.selectOneImage === "function") {
                    hotpoint.selectOneImage(url);
                }
            },

            getMovie: function (movieName) {
                var me = this;

                if (navigator.appName.indexOf("Microsoft") != -1) {
                    return window[movieName];
                } else {
                    return document[movieName];
                }
            },

            linkLegend: function (callout) {
                var self = this;
                
                self.svgOperator.highlightTextByOutData(callout);

            },

            changeLegendList: function (node, $node, tagName) {
                var self = this, el, versions;
                    
                if(tagName === "SELECT") return;
                
                self.$node = $node;
                self.node = node;
                versions = JSON.parse(node.versions);
                self.$legendList.empty();
                
                for(var i = 0; i< versions.length; i++){
                	el = $("<option>").attr({
						"data-id": node.id,
						"data-code": versions[i].legendCode,
						"data-systemCode": node.systemCode,
						"data-leaf": node.leaf
					});
                	if(versions[i].note && versions[i].note.length > 0){
                		el.text(versions[i].legendCode + " " + versions[i].name + "（" + versions[i].note + "）");
                	}else{
                		el.text(versions[i].legendCode + " " + versions[i].name);
                	}
                	
                	self.$legendList.append(el);
                }
                var legendCode = $("#legend-legendCode").val();
                $("#legend-list option").each(function(){
                	if($(this).attr("data-code") == legendCode){
                		$(this).attr("selected",true);
                	}
                });
                
                //下拉列表大于2时提用户点击
				if(versions.length>1)
					document.getElementById('show_legend_more').style.display = "";
				else
					document.getElementById('show_legend_more').style.display = "none";
				
                self.$legendList.change();
            }
        };

        return Legend;
    });
