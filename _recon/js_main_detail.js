require(["settings", "grid", "supersession", "note", "conjunction", "kit", "saleReman", "declareInfo", "orderQty", "jquery", "domReady!"],
    function(settings, grid, Supersession, Note, Conjunction, Kit, SaleReman, DeclareInfo, OrderQty) {
		var language = settings.i18n;
        var detail = {

            init: function() {
                var self = this;

                self.bindDomEls();
                self.initComponent();
                self.bindEvent();
                self.settingBuyStatus();
                if(self.$thumbnailsImg.attr("data-img") === "pic") self.calculate(self.$thumbnails.find("img:first"));
            },

            bindDomEls: function() {
                var self = this;
				
				self.$shoppingCart = $("#shopping-order-qty");
                self.$partsMpq = $("#parts-mpq");
                self.$switchEl = $("#switch");
                self.$switchEls = self.$switchEl.find("li");
                self.$switchContentWrap = $("#tab-content-wrap");
                self.$switchContentEls = self.$switchContentWrap.find("div[data-area='tab-content']");
                self.$btnBuy = $("#btn-buy");
                self.$partNo = $("#qty-partNO");
                self.$conjunctionGrid = $("#conjunction-grid");
                self.$kitGrid = $("#kit-grid");
                self.$saleRemanGrid = $("#saleReman-grid");
                self.$thumbnailsImg = $("#thumbnails-img");
                self.$thumbnails = $("#thumbnails");
                self.$preServed4= $("#qty-preServed4");
            },

            bindEvent: function() {
                var self = this;

                self.$switchEl.on("click", "li", function() {
                    self.switchContent($(this).index());
                });

                self.$btnBuy.on("click", function() {
                    if ($(this).hasClass('btn-disabled')) return;
                    if ($(this).attr("data-visible") === 'true'){
                    	self.openPartsQtyDialog();
                    }
                });

                self.$conjunctionGrid.on("click", "a[data-action='buy']", function(e) {
                    self.openQtyDialog(e);
                });

                self.$kitGrid.on("click", "a[data-action='buy']", function(e) {
                    self.openQtyDialog(e);
                });

                self.$saleRemanGrid.on("click", "a[data-action='buy']", function(e) {
                    self.openQtyDialog(e);
                });

                self.$thumbnails.on("mouseover", "img", function(e) {
                	self.calculate($(e.target));
                });
            },

            switchContent: function(index) {
                var self = this;

                self.$switchEls.removeClass();
                self.$switchEls.eq(index).addClass("selected");

                self.$switchContentEls.hide();
                self.$switchContentEls.eq(index).show();

            },

            initComponent: function() {
                var self = this;

                self.supersession = new Supersession();
                self.note = new Note();
                self.conjunction = new Conjunction();
                self.kit = new Kit();
                self.saleReman = new SaleReman();
                self.declareInfo = new DeclareInfo();

            },

            openPartsQtyDialog: function() {                
                var self = this,
                    partNO = self.$partNo.text(),
                    mpq = self.$partsMpq.text(),
                    preServed4=self.$preServed4.text(),
                    
                    params = {
                        partNO: partNO,
                        mpq: mpq,
                        preServed4:preServed4
                    };
				//alert(">>partNO="+self.$partNO.text()+">>preServed4="+self.$preServed4.text());//
            
                amplify.publish("open-order-qty", params);
            },

            openQtyDialog: function(e) {
                var self = this,
                    partNO = $(e.target).attr("data-partNO"),
                    mpq = $(e.target).attr("data-mpq"),
                    preServed4 = $(e.target).attr("data-preServed4"),
                    params = {
                        "partNO": partNO,
                        mpq: mpq,
                        preServed4:preServed4
                    };

                amplify.publish("open-order-qty", params);
            },
            
            calculate: function ($sender) {
            	var self = this,
            		img = new Image(),
            		src = $sender.attr("src"),
            		containerW = self.$thumbnailsImg.parent().width(),
            		containerH = self.$thumbnailsImg.parent().height(),
            		scaling, wScaling, hScaling, flag, imgW, imgH;
            		
            	img.src = src;
            	imgW = img.width;
            	imgH = img.height;
            	
            	if(imgW > containerW || imgH > containerH){
	            	wScaling = 1 - (imgW - containerW) / imgW;
	            	hScaling = 1 - (imgH - containerH) / imgH;
	            	flag = "over";
            	}else if(imgW < containerW && imgH < containerH){
            		wScaling = 1 - (containerW - imgW) / containerW;
            		hScaling = 1 - (containerH - imgH) / containerH;
            		flag = "less";
            	} else {
            		flag = "equal";
            	}
            	   	
            	if(flag === "over"){
            		wScaling > hScaling ? scaling = hScaling : scaling = wScaling;
            	}else if(flag === "less"){
            		wScaling > hScaling ? scaling = wScaling : scaling = hScaling;
            	}
            	
            	self.changeImg(scaling, imgW, imgH, flag, containerH, src);            	
            },
            
            changeImg: function (scaling, imgW, imgH, flag, containerH, src) {
            	var self = this,
            		width, height, top = 0;
            	
            	if(flag === "over"){
	            	width = imgW * scaling;
	        		height = imgH * scaling;
            	}else if(flag === "less"){
            		width = imgW / scaling;
            		height = imgH / scaling;            		
            	}else{
            		width = imgW;
            		height = imgH;
            	}            	
            	
            	top = (containerH - height) / 2;
            	
            	self.changeThumbnailsImg(src, width, height, top);
            },            

            changeThumbnailsImg: function(src, width, height, top) {
                var self = this;                
                
                self.$thumbnailsImg
                	.attr("src", src)
                	.css({
                		"width": width - 2 + "px",
                		"height": height - 2 + "px",
                		"margin": "0 auto",
                		"margin-top": top + "px"
                		});
            },
            
            settingBuyStatus: function() {
                var self = this,
                    disableClass = "btn-disabled",
                    flag = self.$btnBuy.attr("data-flag");
                if (flag === "true") {
                    self.$btnBuy.removeClass(disableClass);
                }
            }
        };

        detail.init();
    });