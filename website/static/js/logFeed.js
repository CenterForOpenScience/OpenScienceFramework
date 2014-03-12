/**
 * Renders a log feed.
 *
 * Example useage:
 *     $script(['/static/js/logFeed.js'], function() {
 *         var logFeed = new LogFeed('#logFeed', {data: '/api/v1/watched/logs/'})
 *     });
 */
this.LogFeed = (function(ko, $, global, moment) {
    'use strict';
    /**
     * Log model.
     */
    var Log = function(params) {
        var self = this;
        self.action = params.action;
        self.date = new FormattableDate(params.date);
        self.nodeCategory = params.nodeCategory;
        self.nodeDescription = params.nodeDescription;
        self.nodeTitle = params.nodeTitle;
        self.contributor = params.contributor;
        self.contributors = params.contributors;
        self.nodeUrl = params.nodeUrl;
        self.userFullName = params.userFullName;
        self.userURL = params.userURL;
        self.apiKey = params.apiKey;
        self.params = params.params; // Extra log params
        self.wikiUrl = ko.computed(function() {
            return self.nodeUrl + "wiki/" + self.params.page;
        });

        /**
         * Given an item in self.contributors, return its anchor element representation.
         */
        self._asContribLink = function(person) {
            return '<a class="contrib-link" href="/profile/' + person.id + '/">'
                    + person.fullname + "</a>"
        };

        /**
         * Return the html for a comma-delimited list of contributor links, formatted
         * with correct list grammar.
         * e.g. "Dasher and Dancer", "Comet, Cupid, and Blitzen"
         */
        self.displayContributors = ko.computed(function(){
            var ret = "";
            for(var i=0; i < self.contributors.length; i++){
                var person = self.contributors[i];
                if(i == self.contributors.length - 1 && self.contributors.length > 2){
                    ret += " and ";
                }
                if (person.registered)
                    ret += self._asContribLink(person);
                else
                    ret += '<span>' + person.fullname + '</span>';
                if (i < self.contributors.length - 1 && self.contributors.length > 2){
                    ret += ", ";
                } else if (i < self.contributors.length - 1 && self.contributors.length == 2){
                    ret += " and ";
                }
            }
            return ret;
        })
    };

    /**
     * View model for a log list.
     * @param {Log[]} logs An array of Log model objects to render.
     * @param url the url ajax request post to
     */
    var LogsViewModel = function(logs, url) {
        if (logs.length<10){
            $(".moreLogs").hide();
        }
        var self = this;
        self.logs = ko.observableArray(logs);
        var page_num=  0;
        self.url = url;

        //send request to get more logs when the more button is clicked
        self.moreLogs = function(){
            page_num+=1;
            $.ajax({
                url: self.url,
                data:{
                    pageNum:page_num
                },
                type: "get",
                cache: false,
                success: function(response){
                    // Initialize LogViewModel
                    var logs = response['logs'];
                    if (logs.length<10){
                        $(".moreLogs").hide();
                    }
                    var logModelObjects = createLogs(logs);  // Array of Log model objects
                    for(var i=0;i<logModelObjects.length;i++)
                    {
                        self.logs.push(logModelObjects[i]);
                    }
                }
            });
        };

        self.tzname = ko.computed(function() {
            var logs = self.logs();
            if (logs.length) {
                var tz =  moment(logs[0].date).format('ZZ');
                return tz;
            }
            return '';
        });
    };

    /**
     * Create an Array of Log model objects from data returned from an endpoint
     * @param  {Object[]} logData Log data returned from an endpoint.
     * @return {Log[]}         Array of Log objects.
     */
    var createLogs = function(logData){
        var mappedLogs = $.map(logData, function(item) {
            return new Log({
                "action": item.action,
                "date": item.date,
                "nodeCategory": item.node.category,
                "contributor": item.contributor,
                "contributors": item.contributors,
                "nodeUrl": item.node.url,
                "userFullName": item.user.fullname,
                "userURL": item.user.url,
                "apiKey": item.api_key,
                "params": item.params,
                "nodeTitle": item.node.title,
                "nodeDescription": item.params.description_new
            })
        });
        return mappedLogs;
    };

    ////////////////
    // Public API //
    ////////////////

    var defaults = {
        /** Selector for the progress bar. */
        progBar: '#logProgressBar'
    };


    var initViewModel = function(self, logs, url){
        self.logs = createLogs(logs);
        self.viewModel = new LogsViewModel(self.logs, url);
        self.init();
    }
    /**
     * A log list feed.
     * @param {string} selector
     * @param {string or Array} data
     * @param {object} options
     */

    function LogFeed(selector, data, options) {
        var self = this;
        self.selector = selector;
        self.$element = $(selector);
        self.options = $.extend({}, defaults, options);
        self.$progBar = $(self.options.progBar);
        if (Array.isArray(data)) { // data is an array of log object from server
            initViewModel(self,data, self.options.url);
        } else { // data is a URL
            $.getJSON(data, function(response) {
                  initViewModel(self,response.logs,data);
            });
        }
    }

    LogFeed.prototype.init = function() {
        var self = this;
        self.$progBar.hide();
        ko.cleanNode(self.$element[0]);
        ko.applyBindings(self.viewModel, self.$element[0]);
    };

    return LogFeed;

})(ko, jQuery, window, moment);
