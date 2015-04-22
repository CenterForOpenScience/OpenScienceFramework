'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
require('knockout.validation');
require('knockout.punches');
ko.punches.enableAll();
require('knockout-sortable');

var $osf = require('./osfHelpers');
var koHelpers = require('./koHelpers');
require('js/objectCreateShim');

var socialRules = {
    orcid: /orcid\.org\/([-\d]+)/i,
    researcherId: /researcherid\.com\/rid\/([-\w]+)/i,
    scholar: /scholar\.google\.com\/citations\?user=(\w+)/i,
    twitter: /twitter\.com\/(\w+)/i,
    linkedIn: /linkedin\.com\/profile\/view\?id=(\d+)/i,
    impactStory: /impactstory\.org\/([\w\.-]+)/i,
    github: /github\.com\/(\w+)/i
};

var cleanByRule = function(rule) {
    return function(value) {
        var match = value.match(rule);
        if (match) {
            return match[1];
        }
        return value;
    };
};

var noop = function() {};

var SerializeMixin = function() {};

/** Serialize to a JS Object. */
SerializeMixin.prototype.serialize = function() {
    var self = this;
    return ko.toJS(self);
};

SerializeMixin.prototype.unserialize = function(data) {
    var self = this;
    $.each(data || {}, function(key, value) {
        if (ko.isObservable(self[key])) {
            self[key](value);
            // Ensure that validation errors are displayed
            self[key].notifySubscribers();
        }
    });
    return self;
};

/**
    * A mixin to handle custom date serialization on ContentModels with a separate month input.
    *
    * Months are converted to their integer equivalents on serialization
    * for db storage and back to strings on unserialization to display to the user.
    */
var DateMixin = function() {
    var self = this;
    self.months = ['January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'];
    self.endMonth = ko.observable();
    self.endYear = ko.observable().extend({
        required: {
            onlyIf: function() {
                return !!self.endMonth();
            },
            message: 'Please enter a year for the end date.'
        },
        year: true,
        pyDate: true
    });
    self.ongoing = ko.observable(false);
    self.displayDate = ko.observable(' ');
    self.endView = ko.computed(function() {
        return (self.ongoing() ? 'ongoing' : self.displayDate());
    }, self);
    self.startMonth = ko.observable();
    self.startYear = ko.observable().extend({
        required: {
            onlyIf: function() {
                if (!!self.endMonth() || !!self.endYear() || self.ongoing() === true) {
                    return true;
                }
            },
            message: 'Please enter a year for the start date.'
        },
        year: true,
        pyDate: true
    });

    self.start = ko.computed(function () {
        if (self.startMonth() && self.startYear()) {
            return new Date(self.startYear(),
                    (self.monthToInt(self.startMonth()) - 1).toString());
        } else if (self.startYear()) {
            return new Date(self.startYear(), '0', '1');
        }
    }, self).extend({
        notInFuture: true
    });
    self.end = ko.computed(function() {
        if (self.endMonth() && self.endYear()) {
            self.displayDate(self.endMonth() + ' ' + self.endYear());
            return new Date(self.endYear(),
                    (self.monthToInt(self.endMonth()) - 1).toString());
        } else if (!self.endMonth() && self.endYear()) {
            self.displayDate(self.endYear());
            return new Date(self.endYear(), '0', '1');
        }
    }, self).extend({
        notInFuture:true,
        minDate: self.start
    });
    self.clearEnd = function() {
        self.endMonth('');
        self.endYear('');
        return true;
    };
};

DateMixin.prototype.monthToInt = function(value) {
    var self = this;
    if (value !== undefined) {
        return self.months.indexOf(value) + 1;
    }
};

DateMixin.prototype.intToMonth = function(value) {
    var self = this;
    if (value !== undefined) {
        return self.months[(value - 1)];
    }
};

DateMixin.prototype.serialize = function() {
    var self = this;
    var content = ko.toJS(self);
    var startMonthInt = self.monthToInt(self.startMonth());
    var endMonthInt = self.monthToInt(self.endMonth());
    content.startMonth = startMonthInt;
    content.endMonth = endMonthInt;

    return content;
};

DateMixin.prototype.unserialize = function(data) {
    var self = this;
    SerializeMixin.prototype.unserialize.call(self, data);

    var startMonth = self.intToMonth(self.startMonth());
    var endMonth = self.intToMonth(self.endMonth());
    self.startMonth(startMonth);
    self.endMonth(endMonth);

    return self;
};

/** A mixin to set, keep and revert the state of a model's fields
    *
    *  A trackedProperties list attribute must defined, containing all fields
    *  to be tracked for changes. Generally, this will be any field that is
    *  filled from an external source, and will exclude calculated fields.
    * */
var TrackedMixin = function() {
    var self = this;
    self.originalValues = ko.observable();
};

/** Determine is the model has changed from its original state */
TrackedMixin.prototype.dirty = function() {
    var self = this;
    return ko.toJSON(self.trackedProperties) !== ko.toJSON(self.originalValues());
};

/** Store values in tracked fields for future use */
TrackedMixin.prototype.setOriginal = function () {
    var self = this;
    self.originalValues(ko.toJS(self.trackedProperties));
};

/** Restore fields to their values as of when setOriginal was called */
TrackedMixin.prototype.restoreOriginal = function () {
    var self = this;
    for (var i=0; i<self.trackedProperties.length; i++) {
        self.trackedProperties[i](self.originalValues()[i]);
    }
};

var BaseViewModel = function(urls, modes, preventUnsaved) {
    var self = this;

    self.urls = urls;
    self.modes = modes || ['view'];
    self.viewable = $.inArray('view', modes) >= 0;
    self.editAllowed = $.inArray('edit', self.modes) >= 0;
    self.editable = ko.observable(self.editAllowed);
    self.mode = ko.observable(self.editable() ? 'edit' : 'view');

    self.original = ko.observable();
    self.tracked = [];  // Define for each view model that inherits

    // Must be set after isValid is defined in inherited view models
    self.hasValidProperty = ko.observable(false);
    self.requiredFieldEmpty = ko.observable(false);

    // Warn on URL change if dirty
    if (preventUnsaved !== false) {
        $(window).on('beforeunload', function() {
            if (self.dirty()) {
                return 'You have unsaved changes to your settings.';
            }
        });
    }

    // Warn on tab change if dirty
    $('body').on('show.bs.tab', function() {
        if (self.dirty()) {
            $osf.growl('There are unsaved changes.',
                    'Please save or discard your changes before switching ' +
                    'tabs.');
            return false;
        }
        return true;
    });
    
    self.message = ko.observable();
    self.messageClass = ko.observable();
    self.showMessages = ko.observable(false);
};

BaseViewModel.prototype.changeMessage = function(text, css, timeout) {
    var self = this;
    self.message(text);
    var cssClass = css || 'text-info';
    self.messageClass(cssClass);
    if (timeout) {
        // Reset message after timeout period
        setTimeout(
            function() {
                self.message('');
                self.messageClass('text-info');
            },
            timeout
        );
    }
};

BaseViewModel.prototype.handleSuccess = function() {
    var self = this;
    if ($.inArray('view', self.modes) >= 0) {
        self.mode('view');
    } else {
        self.changeMessage(
            'Settings updated',
            'text-success',
            5000
        );
    }
};

BaseViewModel.prototype.handleError = function(response) {
    var self = this;
 //   console.log("in BaseViewModel.prototype.handleError, response is " + JSON.stringify(response));
    var defaultMsg = 'Could not update settings';
    var msg = response.message_long || defaultMsg;
    self.changeMessage(
        msg,
        'text-danger',
        5000
    );
};

BaseViewModel.prototype.setOriginal = function() {};

BaseViewModel.prototype.dirty = function() { return false; };

BaseViewModel.prototype.fetch = function(callback) {
    var self = this;
    callback = callback || noop;
    $.ajax({
        type: 'GET',
        url: self.urls.crud,
        dataType: 'json',
        success: [self.unserialize.bind(self), self.setOriginal.bind(self), callback.bind(self)],
        error: self.handleError.bind(self, 'Could not retrieve your data')
    });
};

BaseViewModel.prototype.edit = function() {
    var self = this;
    if (self.editable() && this.editAllowed) {
        self.mode('edit');
    }
};

BaseViewModel.prototype.cancel = function(data, event) {
    var self = this;
    event && event.preventDefault();

    if (self.dirty()) {
        bootbox.confirm({
            title: 'Discard changes?',
            message: 'Are you sure you want to discard your unsaved changes?',
            callback: function(confirmed) {
                if (confirmed) {
                    self.restoreOriginal();
                    if ($.inArray('view', self.modes) !== -1) {
                        self.mode('view');
                    }
                }
            }
        });
    } else {
        if ($.inArray('view', self.modes) !== -1) {
            self.mode('view');
        }
    }

};

BaseViewModel.prototype.submit = function() {
    var self = this;
//    console.log("In BaseViewModel.prototype.submit, self is " + data);
    if (self.hasValidProperty() && self.isValid()) {
        if (self.requiredFieldEmpty()) {
            $osf.growl('Please enter Required field before pressing "Save"');            
        }
          else {
            $osf.putJSON(
                self.urls.crud,
                self.serialize()
            ).done(
                self.handleSuccess.bind(self)
            ).done(
                self.setOriginal.bind(self)
            ).fail(
                self.handleError.bind(self)
            );
        } 
    } 
    else {
            self.showMessages(true);
    }

};

var NameViewModel = function(urls, modes, preventUnsaved, fetchCallback) {
    var self = this;
    BaseViewModel.call(self, urls, modes, preventUnsaved);
    fetchCallback = fetchCallback || noop;
    TrackedMixin.call(self);

    self.full = koHelpers.sanitizedObservable().extend({required: true, trimmed: true});
    self.given = koHelpers.sanitizedObservable().extend({trimmed: true});
    self.middle = koHelpers.sanitizedObservable().extend({trimmed: true});
    self.family = koHelpers.sanitizedObservable().extend({trimmed: true});
    self.suffix = koHelpers.sanitizedObservable().extend({trimmed: true});
    
    self.trackedProperties = [
        self.full,
        self.given,
        self.middle,
        self.family,
        self.suffix
    ];

    var validated = ko.validatedObservable(self);
    self.isValid = ko.computed(function() {
        return validated.isValid();
    });
    
   self.requiredFieldEmpty = ko.computed(function() {
        if (self.full() == "") {
        return true;        
        }
        else return false;
    });

var myViewModel = ko.validatedObservable({
   property1: ko.computed(function() {
       return  self.full;
   }).extend({ required: true })
});


//     self.validatedFields = ko.validatedObservable($.extend({}, self.trackedProperties));

// self.isValid2 = ko.computed(function() {
//         return self.validatedFields.isValid();
//     });

    
//    var result = ko.validation.group(self, { deep: true });
    
//    self.fullIsValid = ko.computed(function() {
//        return self.full.isValid()
//    });
    
//    console.log("self.full().isvalid is " + ko.toJS(self.full.isValid()));

    
    self.hasValidProperty(true);

    self.citations = ko.observable();

    self.hasFirst = ko.computed(function() {
        return !! self.full();
    });

    self.impute = function(callback) {
        var cb = callback || noop;
        if (! self.hasFirst()) {
            return;
        }
        return $.ajax({
            type: 'GET',
            url: urls.impute,
            data: {
                name: self.full()
            },
            dataType: 'json',
            success: [self.unserialize.bind(self), cb],
            error: self.handleError.bind(self, 'Could not fetch names')
        });
    };

    var initials = function(names) {
        return names
            .split(' ')
            .map(function(name) {
                return name[0].toUpperCase() + '.';
            })
            .filter(function(initial) {
                return initial.match(/^[a-z]/i);
            }).join(' ');
    };

    var suffix = function(suffix) {
        var suffixLower = suffix.toLowerCase();
        if ($.inArray(suffixLower, ['jr', 'sr']) !== -1) {
            suffix = suffix + '.';
            suffix = suffix.charAt(0).toUpperCase() + suffix.slice(1);
        } else if ($.inArray(suffixLower, ['ii', 'iii', 'iv', 'v']) !== -1) {
            suffix = suffix.toUpperCase();
        }
        return suffix;
    };

    self.citeApa = ko.computed(function() {
        var cite = self.family();
        var given = $.trim(self.given() + ' ' + self.middle());

        if (given) {
            cite = cite + ', ' + initials(given);
        }
        if (self.suffix()) {
            cite = cite + ', ' + suffix(self.suffix());
        }
        return cite;
    });

    self.citeMla = ko.computed(function() {
        var cite = self.family();
        if (self.given()) {
            cite = cite + ', ' + self.given();
            if (self.middle()) {
                cite = cite + ' ' + initials(self.middle());
            }
        }
        if (self.suffix()) {
            cite = cite + ', ' + suffix(self.suffix());
        }
        return cite;
    });

    self.fetch(fetchCallback);
};
NameViewModel.prototype = Object.create(BaseViewModel.prototype);
$.extend(NameViewModel.prototype, SerializeMixin.prototype, TrackedMixin.prototype);

/*
 * Custom observable for use with external services.
 */
var extendLink = function(obs, $parent, label, baseUrl) {
    obs.url = ko.computed(function($data, event) {
        // Prevent click from submitting form
        event && event.preventDefault();
        if (obs()) {
            return baseUrl ? baseUrl + obs() : obs();
        }
        return '';
    });

    obs.hasAddon = ko.computed(function() {
        return $parent.addons()[label] !== undefined;
    });

    obs.importAddon = function() {
        if (obs.hasAddon()) {
            obs($parent.addons()[label]);
        }
    };

    return obs;
};

var SocialViewModel = function(urls, modes) {
    var self = this;
    BaseViewModel.call(self, urls, modes);
    TrackedMixin.call(self);

    self.addons = ko.observableArray();

    self.personal = extendLink(
        // Note: Apply extenders in reverse order so that `ensureHttp` is
        // applied before `url`.
        ko.observable().extend({
            trimmed: true,
            url: true,
            ensureHttp: true
        }),
        self, 'personal'
    );
    self.orcid = extendLink(
        ko.observable().extend({trimmed: true, cleanup: cleanByRule(socialRules.orcid)}),
        self, 'orcid', 'http://orcid.org/'
    );
    self.researcherId = extendLink(
        ko.observable().extend({trimmed: true, cleanup: cleanByRule(socialRules.researcherId)}),
        self, 'researcherId', 'http://researcherId.com/rid/'
    );
    self.twitter = extendLink(
        ko.observable().extend({trimmed: true, cleanup: cleanByRule(socialRules.twitter)}),
        self, 'twitter', 'https://twitter.com/'
    );
    self.scholar = extendLink(
        ko.observable().extend({trimmed: true, cleanup: cleanByRule(socialRules.scholar)}),
        self, 'scholar', 'http://scholar.google.com/citations?user='
    );
    self.linkedIn = extendLink(
        ko.observable().extend({trimmed: true, cleanup: cleanByRule(socialRules.linkedIn)}),
        self, 'linkedIn', 'https://www.linkedin.com/profile/view?id='
    );
    self.impactStory = extendLink(
        ko.observable().extend({trimmed: true, cleanup: cleanByRule(socialRules.impactStory)}),
        self, 'impactStory', 'https://www.impactstory.org/'
    );
    self.github = extendLink(
        ko.observable().extend({trimmed: true, cleanup: cleanByRule(socialRules.github)}),
        self, 'github', 'https://github.com/'
    );

    
    self.trackedProperties = [
        self.personal,
        self.orcid,
        self.researcherId,
        self.twitter,
        self.scholar,
        self.linkedIn,
        self.impactStory,
        self.github
    ];

    var validated = ko.validatedObservable(self);
    self.isValid = ko.computed(function() {
        return validated.isValid();
    });
    self.hasValidProperty(true);

    self.values = ko.computed(function() {
        return [
            {label: 'Personal Site', text: self.personal(), value: self.personal.url()},
            {label: 'ORCID', text: self.orcid(), value: self.orcid.url()},
            {label: 'ResearcherID', text: self.researcherId(), value: self.researcherId.url()},
            {label: 'Twitter', text: self.twitter(), value: self.twitter.url()},
            {label: 'GitHub', text: self.github(), value: self.github.url()},
            {label: 'LinkedIn', text: self.linkedIn(), value: self.linkedIn.url()},
            {label: 'ImpactStory', text: self.impactStory(), value: self.impactStory.url()},
            {label: 'Google Scholar', text: self.scholar(), value: self.scholar.url()}
        ];
    });

    self.hasValues = ko.computed(function() {
        var values = self.values();
        for (var i=0; i<self.values().length; i++) {
            if (values[i].value) {
                return true;
            }
        }
        return false;
    });

    self.fetch();
};
SocialViewModel.prototype = Object.create(BaseViewModel.prototype);
$.extend(SocialViewModel.prototype, SerializeMixin.prototype, TrackedMixin.prototype);

var ListViewModel = function(ContentModel, urls, modes) {

    var self = this;
    BaseViewModel.call(self, urls, modes);

    self.ContentModel = ContentModel;
    self.contents = ko.observableArray();
    
//    self.institutionArray = ko.computed( function() {
//        self.contents().institution;
//    });

    self.tracked = self.contents;

    self.canRemove = ko.computed(function() {
        return self.contents().length > 1;
    });

    self.isValid = ko.computed(function() {
        for (var i=0; i<self.contents().length; i++) {
            if (! self.contents()[i].isValid()) {
                return false;
            }
        }
        return true;
    });

    
    self.hasBlankInstitution = ko.computed(function() {
//        console.log("In hasBlankInstitution");
        for (var i=0; i<self.contents().length; i++) {
            if (self.contents()[i].institution() == "") { 
                return true; 
            }
        }
        return false;
    });
    
//    self.hasBlankObject = ko.computed(function() {
////        console.log("In hasBlankInstitution");
////        for (var i=0; i<self.tracked().length; i++) {
//            if (self.institution == "" &&
//                self.department == "")
//                return true; 
//            else 
//                return false;
//    });
    
    
//    self.hasBlankContentObject = ko.computed(function() {
//        console.log("In hasBlankContentObject");
//        for (var i=0; i<self.contents().length; i++) {
//            if (self.contents()[i].trackedProperties)
//            for (var j=0; i < self.contents()[i].trackedProperties.length; j++) {
//                if (self.contents()[i].trackedProperties[j] != null)
//                    return true
//            }
//        }
//        return false;    
//            
//            //            for (var j=0; i< self.contents()[i].trackedProperties().length; j++) {
////                if (!trackedProperties) { 
////                    return false; 
////                }
////            }
////        }
////        if (typeof self.contents()[0].trackedProperties() !== undefined)
////            return self.contents()[0].trackedProperties();
////        else return "yourmomma"
//    });

    
    self.hasMultiple = ko.computed(function() {
//        console.log("Not In hasBlankInstitution");
        return self.contents().length > 1;
    });
    self.hasValidProperty(true);

    /** Determine if any of the models in the list are dirty
    *
    * Emulates the interface of TrackedMixin.dirty
    * */
    self.dirty = function() {
        // if the length of the list has changed
        if (self.originalItems.length !== self.contents().length) {
            return true;
        }
        for (var i=0; i<self.contents().length; i++) {
            if (
                // object has changed
                self.contents()[i].dirty() ||
                // it's a different object
                self.contents()[i].originalValues() !== self.originalItems[i]
                ) { return true; }
        }
        return false;
    };



    /** Restore all items in the list to their original state
        *
        * Emulates the interface of TrackedMixin.restoreOriginal
        * */
    self.restoreOriginal = function() {
        self.contents([]);

        // We can't trust the original objects, as they're mutable
        for (var i=0; i<self.originalItems.length; i++) {

            // Reconstruct the item
            var item = new self.ContentModel(self);
            item.originalValues(self.originalItems[i]);
            item.restoreOriginal();

            self.contents.push(item);
        }
    };

    /** Store the state of all items in the list
        *
        * Emulates the interface of TrackedMixin.setOriginal
        * */
    self.setOriginal = function() {
        self.originalItems = [];
        for (var i=0; i<self.contents().length; i++) {
            self.contents()[i].hasBlankInstitution = self.hasBlankInstitution();
//            self.contents()[i].hasBlankObject = self.hasBlankObject();
            self.contents()[i].setOriginal();
            self.originalItems.push(self.contents()[i].originalValues());
        }
    };
};
ListViewModel.prototype = Object.create(BaseViewModel.prototype);

ListViewModel.prototype.addContent = function() {
    var self = this;
    self.contents.push(new self.ContentModel(self));
};

ListViewModel.prototype.removeContent = function(content) {
    var self = this;
    var idx = self.contents().indexOf(content);
    self.contents.splice(idx, 1);
};

ListViewModel.prototype.unserialize = function(data) {
    var self = this;
    if(self.editAllowed) {
        self.editable(data.editable);
    } else {
        self.editable(false);
    }
    self.contents(ko.utils.arrayMap(data.contents || [], function (each) {
        return new self.ContentModel(self).unserialize(each);
    }));

    // Ensure at least one item is visible
    if (self.contents().length === 0) {
        self.addContent();
    }

    self.setOriginal();
};

ListViewModel.prototype.serialize = function() {
    self = this;
    var contents = [];
    if (self.hasBlankInstitution())
        console.log("In serialize, hasBlankInstitution");
        console.log("In serialize, contents is " + JSON.stringify(self.contents()));
    
    if (self.contents().length !== 0 && typeof(self.contents()[0].serialize() !== undefined)) {
        for (var i=0; i < self.contents().length; i++) {
 //           if (!self.contents()[i].requiredFieldEmpty()) {
 //           console.log("self.contents()[" + i + "].hasBlankInstitution is " + self.contents()[i].hasBlankInstitution);
                
                contents.push(self.contents()[i].serialize());
 //           }
        }
    }
    else {
        contents = ko.toJS(self.contents);
    }
    console.log("In serialize, contents is " + JSON.stringify(contents));
    return {contents: contents};
};

var JobViewModel = function() {
    var self = this;
    DateMixin.call(self);
    TrackedMixin.call(self);

    self.institution = ko.observable('').extend({required: true, trimmed: true});
    self.department = ko.observable('').extend({trimmed: true});
    self.title = ko.observable('').extend({trimmed: true});
    
    self.trackedProperties = [
        self.institution,
        self.department,
        self.title,
        self.startMonth,
        self.startYear,
        self.endMonth,
        self.endYear
    ];

    var validated = ko.validatedObservable(self);
    self.isValid = ko.computed(function() {
        return validated.isValid();
    });
    
    self.requiredFieldEmpty = ko.computed(function() {
        if (self.institution() == "") {
            return true;        
        }
        else return false;
    });

   self.departmentAndTitleFieldsEmpty = ko.computed(function() {
        if (self.department() == "" && self.title() == "") {
            return true;        
        }
        else return false;
    });
    
};
$.extend(JobViewModel.prototype, DateMixin.prototype, TrackedMixin.prototype);

var SchoolViewModel = function() {
    var self = this;
    DateMixin.call(self);
    TrackedMixin.call(self);

    self.institution = ko.observable('').extend({required: true, trimmed: true});
    self.department = ko.observable('').extend({trimmed: true});
    self.degree = ko.observable('').extend({trimmed: true});

    self.trackedProperties = [
        self.institution,
        self.department,
        self.degree,
        self.startMonth,
        self.startYear,
        self.endMonth,
        self.endYear
    ];

    var validated = ko.validatedObservable(self);
    self.isValid = ko.computed(function() {
        return validated.isValid();
    });
    
    self.requiredFieldEmpty = ko.computed(function() {
        if (self.institution() == "") {
        return true;        
        }
        else return false;
    });

};
$.extend(SchoolViewModel.prototype, DateMixin.prototype, TrackedMixin.prototype);

var JobsViewModel = function(urls, modes) {
    var self = this;
    ListViewModel.call(self, JobViewModel, urls, modes);
    self.fetch();
    
//    self.isValid = ListViewModel.prototype.isValid;
    
};
JobsViewModel.prototype = Object.create(ListViewModel.prototype);

var SchoolsViewModel = function(urls, modes) {
    var self = this;
    ListViewModel.call(self, SchoolViewModel, urls, modes);

    self.fetch();
};
SchoolsViewModel.prototype = Object.create(ListViewModel.prototype);

var Names = function(selector, urls, modes) {
    self.viewModel = new NameViewModel(urls, modes);
    $osf.applyBindings(self.viewModel, selector);
    window.nameModel = self.viewModel;
};

var Social = function(selector, urls, modes) {
    self.viewModel = new SocialViewModel(urls, modes);
    $osf.applyBindings(self.viewModel, selector);
    window.social = self.viewModel;
};

var Jobs = function(selector, urls, modes) {
    self.viewModel = new JobsViewModel(urls, modes);
    $osf.applyBindings(self.viewModel, selector);
    window.jobsModel = self.viewModel;
};

var Schools = function(selector, urls, modes) {
    self.viewModel = new SchoolsViewModel(urls, modes);
    $osf.applyBindings(self.viewModel, selector);
};

module.exports = {
    Names: Names,
    Social: Social,
    Jobs: Jobs,
    Schools: Schools,
    // Expose private viewmodels
    _NameViewModel: NameViewModel
};
