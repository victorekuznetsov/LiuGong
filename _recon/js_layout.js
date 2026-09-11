define(["settings", "ajax", "jquery"],
    function (settings, ajax) {

        var defaultOpts = {
            groupId: "group",
            maskId: "group-mask",
            legendId: "legend",
            partsId: "parts",
            btnGroup: "btn-group-action",
            btnMask: "btn-mask-action"
        };

        var Layout = function (options) {

            this.opts = $.extend({}, defaultOpts, options || {});

            this.init();
        };

        Layout.prototype = {

            init: function () {
                var self = this;

                self.buildDomEls();
                self.bindEvent();
                self.firstLayout();
            },

            buildDomEls: function () {
                var self = this;

                self.$group = $("#" + this.opts.groupId);
                self.$mask = $("#" + this.opts.maskId);
                self.$legend = $("#" + this.opts.legendId);
                self.$parts = $("#" + this.opts.partsId);
                self.$btnGroup = $("#" + this.opts.btnGroup);
                self.$btnMask = $("#" + this.opts.btnMask);
            },

            bindEvent: function () {
                var self = this;


                //change layout width
                $(window).on("resize", function () {
                    if ($(window).width() > 1024) {
                        self.resizeLayout();
                    };
                });

                //group button collapse click event
                self.$btnGroup.on("click", function () {
                    self.clickGroupBtn($(this));
                    self.rememberWidth();
                });

                //mask button expand click event
                self.$btnMask.on("click", function (e) {
                    if (self.$group.is(":visible")) {
                        self.undoGroup();
                        e.stopPropagation();
                    } else {
                        self.expandGroup();
                        e.stopPropagation();
                    }
                });

                //mask span click expand float
                self.$mask.on("click", function (e) {
                    self.expandFloatGroup();
                    e.stopPropagation(e);
                });

                self.$group.mouseleave(function () {
                	if(self.$mask.is(":visible")){
                		self.floatCollapse();
                	}
                });

            },

            showMask: function () {
            	var self = this;

            	self.$mask.show()
	                .animate({"left": "0px"})
	                .find("span")
	                .attr("data-action", "group-expand");
            },

            clickGroupBtn: function ($sender) {
                var self = this;

                self.$mask.find("span").removeAttr("data-action");
                if ($sender.hasClass("group-head-collapse")) {
                    self.collapseGroup();
                }
            },

            collapseGroup: function () {
                var self = this;

                self.$group.animate({"left": (-self.$group.width() - 5) + "px"}, function () {
                    $(this).hide();
                    self.showMask();
                    self.collapseLayout();
                    self.rememberElWidth();
                    if (typeof self.opts.onLayoutExpand === "function") {
                        self.opts.onLayoutExpand.apply(self, []);
                    }
                });
            },

            expandGroup: function () {
                var self = this;

                self.$btnGroup.show();
                self.$mask.animate({"left": (-self.$mask.width() - 5) + "px"}, 50, function () {
                    $(this).hide();
                    self.$group.show()
                        .css("boxShadow", "none")
                        .animate({"left": "5px"}, function () {
                            self.expendLayout();
                            self.rememberElWidth();
                            if (typeof self.opts.onLayoutExpand === "function") {
                                self.opts.onLayoutExpand.apply(self, []);
                            }
                        });
                });
            },

            firstLayout: function () {
                var self = this,
                    windowWidth = $(window).width(),
                    groupWidth = (windowWidth * 0.2) - 10,
                    legendWidth = (windowWidth * 0.3) - 10,
                    partsWidth = (windowWidth * 0.5) - 15;

                if ($(".layresizable")) {
                    self.$group.css("width", self.RgroupWidth - 5 + "px");
                    self.$legend.css({ "width": self.RlegendWidth - 10 + "px", "left": (self.RgroupWidth + 10) + "px" });
                    self.$parts.css({ "width": self.RpartsWidth - 20 + "px", "left": (self.RgroupWidth + self.RlegendWidth + 10) + "px" });
                } else {
                    self.$group.css("width", groupWidth + "px");
                    self.$legend.css({ "width": legendWidth + "px", "left": (groupWidth + 15) + "px" });
                    self.$parts.css({ "width": partsWidth + "px", "left": (groupWidth + legendWidth + 25) + "px" });
                }
            },

            resizeLayout: function () {
            	var self = this,
	            	winWidth = $(window).width(),
	            	groupWidth = winWidth * self.groupScaling;
	            	legendWidth = winWidth * self.legendScaling;
	            	partsWidth = winWidth * self.partsScaling;

	            	if (self.$group.is(":visible")){
            			self.$group.css("width", groupWidth + "px");
            			self.$legend.css({ "width": legendWidth + "px", "left": (groupWidth + 15) + "px" });
        				self.$parts.css({ "width": partsWidth + "px", "left": (groupWidth + legendWidth + 25) + "px" });
	            	} else {
	            		self.$legend.css({ "width": legendWidth + "px", "left": self.$mask.width() + 10 + "px" });
        				self.$parts.css({ "width": partsWidth + "px", "left": (legendWidth + self.$mask.width()) + 20 + "px" });
	            	}
            },

            changeLayout: function () {
                var self = this,
                    windowWidth = $(window).width(),
                    maskWidth = self.$mask.width(),
                    legendWidth = ((windowWidth - maskWidth) * 0.4) - 8,
                    partsWidth = ((windowWidth - maskWidth - 20) * 0.6) - 10;

                self.$legend.css({"width": legendWidth + "px", "left": (maskWidth + 10) + "px"});
                self.$parts.css({"width": partsWidth + "px", "left": (maskWidth + legendWidth + 20) + "px"});
                self.showMask();
            },

            expendLayout: function () {
            	var self = this,
                	legendWidth = self.$legend.width() - self.$group.width() + self.$mask.width() - 10,
                	partsWidth = self.$parts.width();

            	self.$legend.css({ "width": legendWidth + 5 + "px", "left": (self.$group.width() + 15) + "px" });
                self.$parts.css({ "width": partsWidth + "px", "left": (self.$parts.offsetLeft + 10) + "px" });
            },

            collapseLayout: function () {
                var self = this,
                    legendWidth = self.$group.width() - self.$mask.width() + self.$legend.width() - 10;

                self.$legend.css({ "width": legendWidth + 10 + "px", "left": (self.$mask.width() + 10) + "px" });
                self.$parts.css({ "width": self.RpartsWidth - self.$mask.width() + 5 + "px", "left": (self.RgroupWidth + self.RlegendWidth + 10) + "px" });
            },

            expandFloatGroup: function () {
                var self = this;

                if (!self.$group.is(":visible")) {
                    self.floatExpand();
                } else {
                    self.floatCollapse();
                }
            },

            floatExpand: function () {
                var self = this;

                self.$btnGroup.hide();
                self.$group.show()
                    .css({"boxShadow": "1px 2px 9px #A7A7A7"})
                    .animate({"left": self.$mask.width() + "px"});
            },

            floatCollapse: function () {
                var self = this;

                self.$group.animate({"left": (-self.$group.width() - 5) + "px"}, function () {
                    $(this).hide()
                        .css("boxShadow", "none");
                    self.$btnGroup.show();
                });
            },

            undoGroup: function () {
                var self = this;

                if (self.$mask.is(":visible")) {
                    self.expandGroup();
                }
            },

            rememberWidth: function () {
                var self = this;

                self.RwindowWidth = $(window).width();
                self.RgroupWidth = $(".layresizable").children().eq(0).offset().left;
                self.RlegendWidth = $(".layresizable").children().eq(1).offset().left - self.RgroupWidth;
                self.RpartsWidth = self.RwindowWidth - self.RgroupWidth - self.RlegendWidth;
            },

            rememberElWidth: function () {
            	var self = this,
            		winWidth = $(window).width(),
	            	groupWidth = self.$group.width(),
	        		legendWidth = self.$legend.width(),
	        		partsWidth = self.$parts.width();

            	if(self.$group.is(":visible")){
		        	self.groupScaling = 1 - (winWidth - groupWidth) / winWidth;
		        	self.legendScaling = 1 - (winWidth - legendWidth) / winWidth;
		        	self.partsScaling = 1 - (winWidth - partsWidth) / winWidth;
            	}else {
		        	self.legendScaling = 1 - (winWidth - legendWidth) / winWidth;
		        	self.partsScaling = 1 - (winWidth - partsWidth) / winWidth;
            	}
            }

        };

        return Layout;
    });

