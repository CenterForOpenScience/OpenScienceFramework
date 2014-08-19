;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils', 'knockoutpunches'], factory);
    } else {
        global.ApiKeyView  = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    // Enable knockout punches
    ko.punches.enableAll();

    var ViewModel = function(url) {
        var self = this;
        self.url = url;
        self.keys = ko.observableArray([]);
        self.label = ko.observable('');

        self.keysRecieved = function(data) {
            self.keys(data.keys);
        };

        self.createKey = function() {
            $.osf.postJSON(self.url, {label: self.label()}, self.keyCreated, self.ajaxError.bind(this, 'create an API key'));
        };

        self.keyCreated = function(data) {
            self.keys.push({label: self.label(), key: data.key});
            self.label('');
        };

        self.deleteKey = function(key) {
            bootbox.confirm('Are you sure you want to delete this API key?', function(result) {
                if (result) {
                    $.ajax({
                        url: self.url + '?key=' + key.key,
                        type: 'DELETE',
                        success: function() {
                            self.keys.splice(self.keys.indexOf(key), 1);
                        },
                        error: self.ajaxError.bind(this, 'delete this API key')
                    });
                }
            });
        };

        self.ajaxError = function(item) {
            bootbox.alert('Could not ' + item + '. Please refresh the page or ' +
                'contact <a href="mailto: support@cos.io">support@cos.io</a> if the ' +
                'problem persists.');
        };

        function fetch() {
            $.ajax({
                url: self.url,
                type: 'GET',
                success: self.keysRecieved,
                error: self.ajaxError.bind(this, 'fetch your API keys')
            });
        }

        fetch();

    };

    function ApiKeyView(selector, url) {
        // Initialization code
        var self = this;
        self.viewModel = new ViewModel(url);
        window.model = self.viewModel;
        $.osf.applyBindings(self.viewModel, selector);
    }

    return ApiKeyView;

}));
