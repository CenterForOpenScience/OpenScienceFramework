(function(window, document, $) {

    'use strict';
    var $osf = require('js/osfHelpers');

    var defaults = {
        animateTime: 100,
        minViewWidth: 150,
        toggleWidth: 1/3,
        maxWidthProp: 2/3,
        smallScreenSize: 767,
        onClose: function() {},
        onOpen: function() {}
    };

    var CommentPane = CommentPane || function(selector, options) {
        var self = this;

        var $pane = $(selector);
        var $handle = $('.cp-handle');
        var $sidebar = $pane.find('.cp-sidebar');
        var $bar = $pane.find('.cp-bar');
        var $toggleElm = $.merge($pane, $sidebar);

        $handle.tooltip();

        options = $.extend({}, defaults, options);
        if (options.maxWidthProp < options.toggleWidth) {
            throw(
                'Option `toggleWidth` must be greater than or equal to ' +
                'option `maxWidthProp`.'
            );
        }

        var makeAllElementsUnselectable = function(){
            $(document).children().each(function (index, elm) {
                $(elm).addClass('unselectable');
            });
        };

        var makeAllElementsSelectable = function(){
            $(document).children().each(function (index, elm) {
                $(elm).removeClass('unselectable');
            });
        };

        var getMaxWidth = function() {
            return $(document.body).width() * options.maxWidthProp;
        };

        self.toggle = function() {
            var width;
            if ($pane.width()) {
                width = 0;
                options.onClose.call(self);
            } else {
                var bodyWidth = $(document.body).width();
                if (bodyWidth <= options.smallScreenSize) {
                    width = options.maxWidthProp * bodyWidth;
                } else {
                    width = options.toggleWidth * bodyWidth;
                }
                options.onOpen.call(self);
            }
            $handle.tooltip('hide');
            $toggleElm.animate(
                {width: width},
                options.animateTime,
                function() {
                    if (width) {
                        // Animation complete, so load the comments from Discourse
                        var discourseEmbedFrame = document.getElementById('discourse-embed-frame');
                        var discourseComments = document.getElementById('discourse-comments');
                        if (discourseEmbedFrame) {
                            // force reload.
                            discourseEmbedFrame.src += '';
                        } else if (!discourseComments.discourseBegunLoading) {
                            discourseComments.discourseBegunLoading = true;

                            var discourseUrl = discourseComments.getAttribute('data-discourse-url');
                            if (discourseUrl.endsWith('//')) {
                                discourseUrl = discourseUrl.slice(0, -1);
                            }

                            var topicId = discourseComments.getAttribute('data-discourse-topic-id');
                            // initial load.
                            if (topicId !== 'None') {
                                window.DiscourseEmbed = { discourseUrl: discourseUrl, topicId: topicId };
                                (function() {
                                    var d = document.createElement('script'); d.type = 'text/javascript'; d.async = true;
                                    d.src = DiscourseEmbed.discourseUrl + 'javascripts/embed.js';
                                    d.onload = function() {
                                        var viewOnly = $osf.urlParams().view_only;
                                        if (viewOnly) {
                                            discourseEmbedFrame = document.getElementById('discourse-embed-frame');
                                            discourseEmbedFrame.src += '&view_only=' + viewOnly;
                                        }
                                    };
                                    (document.getElementsByTagName('head')[0] || document.getElementsByTagName('body')[0]).appendChild(d);
                                })();
                            }
                        }
                    }
                }
            );
        };

        var init = function(){
            // Bind drag & drop handlers
            $bar.on('mousedown', function() {
                makeAllElementsUnselectable();
                $(document).on('mousemove', function(event) {
                    var bodyWidth = $(document.body).width();
                    var dragWidth = document.body.clientWidth - event.pageX;
                    var width = Math.min(dragWidth, getMaxWidth()) + 'px';
                    $pane.css('width', width);
                    $('.cp-sidebar').css('width', width);
                });
                $(document).on('mouseup', function(){
                    $(document).off('mousemove');
                    $(document).off('mouseup');
                    makeAllElementsSelectable();
                    if ($pane.width() < options.minViewWidth) {
                        $pane.animate(
                            {width: '0'}, options.animateTime
                        );
                    }
                });
            });

            // Bind toggle handler
            $handle.on('click', self.toggle);
            $('#projectSubnav .navbar-toggle').on('click', function() {
                if ($pane.width()) {
                    self.toggle();
                }
            });

            // Prevent comment pane from getting too big on resize
            $(window).on('resize', function() {
                var maxWidth = getMaxWidth();
                if ($pane.width() > maxWidth) {
                    $toggleElm.width(maxWidth.toString() + 'px');
                }
            });

        };
        init();
    };

    if ((typeof module !== 'undefined') && module.exports) {
        // Load css with webpack if possible
        if (typeof webpackJsonp !== 'undefined') {
            // NOTE: Assumes that the style-loader and css-loader are used for .css files
            require('../vendor/bower_components/At.js/dist/css/jquery.atwho.css');
            require('../css/commentpane.css');
        }
        module.exports = CommentPane;
    }
    if (typeof ender === 'undefined') {
        this.CommentPane = CommentPane;
    }
    if (typeof define === 'function' && define.amd) {
        define(['jquery'], function($) {
            return CommentPane;
        });
    }

}).call(this, window, document, $);
