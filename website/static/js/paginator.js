/**
 * Paginator model
 */
'use strict';
var ko = require('knockout');
var oop = require('js/oop');
var MAX_PAGES_ON_PAGINATOR = 16;
var MAX_PAGES_ON_PAGINATOR_SIDE = 10;

var Paginator = oop.defclass({
    constructor: function() {
        this.numberOfPages = ko.observable(0);
        this.currentPage = ko.observable(0);
        this.paginators = ko.observableArray([]);
    },
    addNewPaginators: function() {
        var self = this;
        self.paginators.removeAll();
        if (self.numberOfPages() > 1) {
            self.paginators.push({
                style: (self.currentPage() === 0) ? 'disabled' : '',
                handler: self.previousPage.bind(self),
                text: '&lt;'
            });
            self.paginators.push({
                style: (self.currentPage() === 0) ? 'active' : '',
                text: '1',
                handler: function() {
                    self.currentPage(0);
                    self.fetchResults();
                }
            });
            if (self.numberOfPages() <= MAX_PAGES_ON_PAGINATOR) {
                for (var i = 1; i < self.numberOfPages() - 1; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            self.currentPage(parseInt(this.text) - 1);
                            self.fetchResults();
                        }
                    });
                }
            } else if (self.currentPage() < MAX_PAGES_ON_PAGINATOR_SIDE - 1) { // One ellipse at the end
                for (var i = 1; i < MAX_PAGES_ON_PAGINATOR_SIDE; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            self.currentPage(parseInt(this.text) - 1);
                            self.fetchResults();
                        }
                    });
                }
                self.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function() {}
                });
            } else if (self.currentPage() > self.numberOfPages() - MAX_PAGES_ON_PAGINATOR_SIDE) { // one ellipses at the beginning
                self.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function() {}
                });
                for (var i = self.numberOfPages() - MAX_PAGES_ON_PAGINATOR_SIDE; i < self.numberOfPages() - 1; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            self.currentPage(parseInt(this.text) - 1);
                            self.fetchResults();
                        }
                    });
                }
            } else { // two ellipses
                self.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function() {}
                });
                for (var i = self.currentPage() - 1; i <= self.currentPage() + 1; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            self.currentPage(parseInt(this.text) - 1);
                            self.fetchResults();
                        }
                    });
                }
                self.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function() {}
                });
            }
            self.paginators.push({
                style: (self.currentPage() === self.numberOfPages() - 1) ? 'active' : '',
                text: self.numberOfPages(),
                handler: function() {
                    self.currentPage(self.numberOfPages() - 1);
                    self.fetchResults();
                }
            });
            self.paginators.push({
                style: (self.currentPage() === self.numberOfPages() - 1) ? 'disabled' : '',
                handler: self.nextPage.bind(self),
                text: '&gt;'
            });
        }
    },
    nextPage: function(){
        this.currentPage(this.currentPage() + 1);
        this.fetchResults();
    },
    previousPage: function(){
        this.currentPage(this.currentPage() - 1);
        this.fetchResults();
    },
    fetchResults: function() {
        throw new Error('Paginator subclass must define a "fetchResults" method.');
    }
});

module.exports = Paginator;
