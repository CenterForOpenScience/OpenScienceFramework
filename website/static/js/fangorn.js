/**
 * Fangorn: Defining Treebeard options for OSF.
 * For Treebeard and _item API's check: https://github.com/caneruguz/treebeard/wiki
 */

'use strict';

var $ = require('jquery');
var m = require('mithril');
var URI = require('URIjs');
var Treebeard = require('treebeard');

var $osf = require('./osfHelpers');
var waterbutler = require('./waterbutler');

// CSS
require('../css/fangorn.css');

var tbOptions;

var tempCounter = 1;

var EXTENSIONS = ['3gp', '7z', 'ace', 'ai', 'aif', 'aiff', 'amr', 'asf', 'asx', 'bat', 'bin', 'bmp', 'bup',
    'cab', 'cbr', 'cda', 'cdl', 'cdr', 'chm', 'dat', 'divx', 'dll', 'dmg', 'doc', 'docx', 'dss', 'dvf', 'dwg',
    'eml', 'eps', 'exe', 'fla', 'flv', 'gif', 'gz', 'hqx', 'htm', 'html', 'ifo', 'indd', 'iso', 'jar',
    'jpeg', 'jpg', 'lnk', 'log', 'm4a', 'm4b', 'm4p', 'm4v', 'mcd', 'md', 'mdb', 'mid', 'mov', 'mp2', 'mp3', 'mp4',
    'mpeg', 'mpg', 'msi', 'mswmm', 'ogg', 'pdf', 'png', 'pps', 'ps', 'psd', 'pst', 'ptb', 'pub', 'qbb',
    'qbw', 'qxd', 'ram', 'rar', 'rm', 'rmvb', 'rtf', 'sea', 'ses', 'sit', 'sitx', 'ss', 'swf', 'tgz', 'thm',
    'tif', 'tmp', 'torrent', 'ttf', 'txt', 'vcd', 'vob', 'wav', 'wma', 'wmv', 'wps', 'xls', 'xpi', 'zip',
    'xlsx', 'py'];

var EXTENSION_MAP = {};
EXTENSIONS.forEach(function(extension) {
    EXTENSION_MAP[extension] = extension;
});
$.extend(EXTENSION_MAP, {
    gdoc: 'docx',
    gsheet: 'xlsx'
});

var ICON_PATH = '/static/img/hgrid/fatcowicons/';

var getExtensionIconClass = function(name) {
    var extension = name.split('.').pop().toLowerCase();
    var icon = EXTENSION_MAP[extension];
    if (icon) {
        return '_' + icon;
    }
    return null;
};

function findByTempID(parent, tmpID){
    var child;
    var item;
    for (var i = 0; i < parent.children.length; i++) {
        child = parent.children[i];
        if (!child.data.tmpID) {
            continue;
        }
        if (child.data.tmpID === tmpID) {
            item = child;
        }
    }
    return item;
}

function cancelUploads (row) {
    var treebeard = this;
    var filesArr = treebeard.dropzone.getQueuedFiles();
    for (var i = 0; i < filesArr.length; i++) {
        var m = filesArr[i];
        if(!row){
            var parent = m.treebeardParent || treebeard.dropzoneItemCache;
            var item = findByTempID(parent, m.tmpID);
            treebeard.dropzone.removeFile(m);
            treebeard.deleteNode(parent.id,item.id);
        } else {
            treebeard.deleteNode(row.parentID,row.id);
            if(row.data.tmpID === m.tmpID){
                treebeard.dropzone.removeFile(m);
            }
        }
    }

}

var cancelUploadTemplate = function(row){
    var treebeard = this;
    return m('.btn.btn-xs.btn-danger.m-l-sm', { 
            'onclick' : function (e) {
                cancelUploads.call(treebeard, row);
            }},
        m('.fa.fa-times'));
}


var cancelAllUploadsTemplate = function(){
    var treebeard = this;
    return m('div', [
        m('span', 'Uploads in progress'),
        m('.btn.btn-xs.m-l-sm.btn-danger', {
            'onclick' : function() { 
                cancelUploads.call(treebeard);
            } 
        }, 'Cancel All Uploads')
    ]);
}


/**
 * Returns custom icons for OSF depending on the type of item
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {Object}  Returns a mithril template with the m() function.
 * @private
 */
function _fangornResolveIcon(item) {
    var privateFolder =  m('div.file-extension._folder_delete', ' '),
        pointerFolder = m('i.fa.fa-link', ' '),
        openFolder  = m('i.fa.fa-folder-open', ' '),
        closedFolder = m('i.fa.fa-folder', ' '),
        configOption = item.data.provider ? resolveconfigOption.call(this, item, 'folderIcon', [item]) : undefined,  // jshint ignore:line
        icon;

    if (item.kind === 'folder') {
        if (item.data.iconUrl) {
            return m('img', {src: item.data.iconUrl, style: {width: '16px', height: 'auto'}});
        }
        if (!item.data.permissions.view) {
            return privateFolder;
        }
        if (item.data.isPointer) {
            return pointerFolder;
        }
        if (item.open) {
            return configOption || openFolder;
        }
        return configOption || closedFolder;
    }
    if (item.data.icon) {
        return m('i.fa.' + item.data.icon, ' ');
    }

    icon = getExtensionIconClass(item.data.name);
    if (icon) {
        return m('div.file-extension', { 'class': icon });
    }
    return m('i.fa.fa-file-text-o');
}

// Addon config registry. this will be populated with add on specific items if any.
Fangorn.config = {};

/**
 * Returns add on specific configurations
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @param {String} key What the option is called in the add on object
 * @this Treebeard.controller
 * @returns {*} Returns the configuration, can be string, number, array, or function;
 */
function getconfig(item, key) {
    if (item && item.data.provider && Fangorn.config[item.data.provider]) {
        return Fangorn.config[item.data.provider][key];
    }
    return undefined;
}

/**
 * Gets a Fangorn config option if it is defined by an addon dev.
 * Calls it with `args` if it's a function otherwise returns the value.
 * If the config option is not defined, returns null
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @param {String} option What the option is called in the add on object
 * @param {Array} args An Array of whatever arguments will be sent with the .apply()
 * @this Treebeard.controller
 * @returns {*} Returns if its a property, runs the function if function, returns null if no option is defined.
 */
function resolveconfigOption(item, option, args) {
    var self = this,  // jshint ignore:line
        prop = getconfig(item, option);
    if (prop) {
        return typeof prop === 'function' ? prop.apply(self, args) : prop;
    }
    return null;
}

/**
 * Inherits a list of data fields from one item (parent) to another.
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @param {Object} parent A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 */
var inheritedFields = ['nodeId', 'nodeUrl', 'nodeApiUrl', 'permissions', 'provider', 'accept'];
function inheritFromParent(item, parent, fields) {
    fields = fields || inheritedFields;
    fields.forEach(function(field) {
        item.data[field] = item.data[field] || parent.data[field];
    });
}

/**
 * Returns custom folder toggle icons for OSF
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {string} Returns a mithril template with m() function, or empty string.
 * @private
 */
function _fangornResolveToggle(item) {
    var toggleMinus = m('i.fa.fa-minus', ' '),
        togglePlus = m('i.fa.fa-plus', ' ');
    // check if folder has children whether it's lazyloaded or not.
    if (item.kind === 'folder' && item.depth > 1) {
        if(!item.data.permissions.view){
            return '';
        }
        if (item.open) {
            return toggleMinus;
        }
        return togglePlus;
    }
    return '';
}

/**
 * Checks if folder toggle is permitted (i.e. contents are private)
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {boolean}
 * @private
 */
function _fangornToggleCheck(item) {

    if (item.data.permissions.view) {
        return true;
    }
    item.notify.update('Not allowed: Private folder', 'warning', 1, undefined);
    return false;
}

/**
 * Find out what the upload URL is for each item
 * Because we use add ons each item will have something different. This needs to be in the json data.
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {String} Returns the url string from data or resolved through add on settings.
 * @private
 */
function _fangornResolveUploadUrl(item, file) {
    var configOption = resolveconfigOption.call(this, item, 'uploadUrl', [item, file]); // jshint ignore:line
    return configOption || waterbutler.buildTreeBeardUpload(item, file);
}

/**
 * Event to fire when mouse is hovering over row. Currently used for hover effect.
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @param event The mouseover event from the browser
 * @this Treebeard.controller
 * @private
 */
function _fangornMouseOverRow(item, event) {
    $('.fg-hover-hide').hide();
    $(event.target).closest('.tb-row').find('.fg-hover-hide').show();
}

/**
 * Runs when dropzone uploadprogress is running, used for updating upload progress in view and models.
 * @param {Object} treebeard The treebeard instance currently being run, check Treebeard API
 * @param {Object} file File object that dropzone passes
 * @param {Number} progress Progress number between 0 and 100
 * @this Dropzone
 * @private
 */
function _fangornUploadProgress(treebeard, file, progress) {
    var parent = file.treebeardParent;

    var item,
        child,
        column,
        msgWithCancel,
        msgWithoutCancel,
        fullRowTemplate = m('span', file.name.slice(0,25) + '... : ' + 'Uploaded ' + Math.floor(progress) + '%'),
        columnTemplate = m('span', 'Uploaded ' + Math.floor(progress) + '%');
    for(var i = 0; i < parent.children.length; i++) {
        child = parent.children[i];
        if(!child.data.tmpID){
            continue;
        }
        if(child.data.tmpID === file.tmpID) {
            item = child;
        }
    }

    // if(treebeard.options.placement === 'dashboard'){
    //     column = null;
    //     msgWithCancel = m('span', [ fullRowTemplate, cancelUploadTemplate.call(treebeard, item) ]);
    //     msgWithoutCancel = fullRowTemplate;
    // } else {
        column = 1;
        msgWithCancel = m('span', [ columnTemplate, cancelUploadTemplate.call(treebeard, item) ]);
        msgWithoutCancel = columnTemplate;
    // }

    if (progress < 100) {
        item.notify.update(msgWithCancel, 'success', column, 0);
    } else {
        item.notify.update(msgWithoutCancel, 'success', column, 2000);
    }
}

/**
 * Runs when dropzone sending method is running, used for updating the view while file is being sent.
 * @param {Object} treebeard The treebeard instance currently being run, check Treebeard API
 * @param {Object} file File object that dropzone passes
 * @param xhr xhr information being sent
 * @param formData Dropzone's formdata information
 * @this Dropzone
 * @returns {*|null} Return isn't really used here by anything else.
 * @private
 */
function _fangornSending(treebeard, file, xhr, formData) {
    treebeard.options.uploadInProgress = true;
    var parent = file.treebeardParent || treebeard.dropzoneItemCache;
    var _send = xhr.send;
    xhr.send = function() {
        _send.call(xhr, file);
    };
    var filesArr = treebeard.dropzone.getQueuedFiles();
    if (filesArr.length  > 1) {
        treebeard.options.iconState.generalIcons[1].on = true;
    }
    var configOption = resolveconfigOption.call(treebeard, parent, 'uploadSending', [file, xhr, formData]);
    return configOption || null;
}

/**
 * Runs when Dropzone's addedfile hook is run.
 * @param {Object} treebeard The treebeard instance currently being run, check Treebeard API
 * @param {Object} file File object that dropzone passes
 * @this Dropzone
 * @returns {*|null}
 * @private
 */
function _fangornAddedFile(treebeard, file) {
    var item = file.treebeardParent;
    if (!_fangornCanDrop(treebeard, item)) {
        return;
    }
    var configOption = resolveconfigOption.call(treebeard, item, 'uploadAdd', [file, item]);

    var tmpID = tempCounter++;

    file.tmpID = tmpID;
    file.url = _fangornResolveUploadUrl(item, file);
    file.method = _fangornUploadMethod(item);

    var blankItem = {       // create a blank item that will refill when upload is finished.
        name: file.name,
        kind: 'file',
        provider: item.data.provider,
        children: [],
        permissions: {
            view: false,
            edit: false
        },
        tmpID: tmpID
    };
    var newitem = treebeard.createItem(blankItem, item.id);
    return configOption || null;
}

function _fangornCanDrop(treebeard, item) {
    var canDrop = resolveconfigOption.call(treebeard, item, 'canDrop', [item]);
    if (canDrop === null) {
        canDrop = item.data.provider && item.kind === 'folder' && item.data.permissions.edit;
    }
    return canDrop;
}

/**
 * Runs when Dropzone's dragover event hook is run.
 * @param {Object} treebeard The treebeard instance currently being run, check Treebeard API
 * @param event DOM event object
 * @this Dropzone
 * @private
 */
function _fangornDragOver(treebeard, event) {
    var dropzoneHoverClass = 'fangorn-dz-hover',
        closestTarget = $(event.target).closest('.tb-row'),
        itemID =  parseInt(closestTarget.attr('data-id')),
        item = treebeard.find(itemID);
    $('.tb-row').removeClass(dropzoneHoverClass).removeClass(treebeard.options.hoverClass);
    if (item !== undefined) {
        if (_fangornCanDrop(treebeard, item)) {
            closestTarget.addClass(dropzoneHoverClass);
        }
    }
}

/**
 * Runs when Dropzone's complete hook is run after upload is completed.
 * @param {Object} treebeard The treebeard instance currently being run, check Treebeard API
 * @param {Object} file File object that dropzone passes
 * @this Dropzone
 * @private
 */
function _fangornComplete(treebeard, file) {
    var item = file.treebeardParent;
    resolveconfigOption.call(treebeard, item, 'onUploadComplete', [item]);
    _fangornOrderFolder.call(treebeard, item);
}

/**
 * Runs when Dropzone's success hook is run.
 * @param {Object} treebeard The treebeard instance currently being run, check Treebeard API
 * @param {Object} file File object that dropzone passes
 * @param {Object} response JSON response from the server
 * @this Dropzone
 * @private
 */
function _fangornDropzoneSuccess(treebeard, file, response) {
    treebeard.options.uploadInProgress = false;
    var parent = file.treebeardParent,
        item,
        revisedItem,
        child;
    for (var i = 0; i < parent.children.length; i++) {
        child = parent.children[i];
        if (!child.data.tmpID){
            continue;
        }
        if (child.data.tmpID === file.tmpID) {
            item = child;
        }
    }
    // RESPONSES
    // OSF : Object with actionTake : "file_added"
    // DROPBOX : Object; addon : 'dropbox'
    // S3 : Nothing
    // GITHUB : Object; addon : 'github'
    // Dataverse : Object, actionTaken : file_uploaded
    revisedItem = resolveconfigOption.call(treebeard, item.parent(), 'uploadSuccess', [file, item, response]);
    if (!revisedItem && response) {
        item.data = response;
        inheritFromParent(item, item.parent());
    }
    if (item.data.tmpID) {
        item.data.tmpID = null;
    }
    // Remove duplicates if file was updated
    var status = file.xhr.status;
    if (status === 200) {
        parent.children.forEach(function(child) {
            if (child.data.name === item.data.name && child.id !== item.id) {
                child.removeSelf();
            }
        });
    }
    treebeard.options.iconState.generalIcons[1].on = false;
    treebeard.redraw();
}

/**
 * runs when Dropzone's error hook runs. Notifies user with error.
 * @param {Object} treebeard The treebeard instance currently being run, check Treebeard API
 * @param {Object} file File object that dropzone passes
 * @param message Error message returned
 * @private
 */
var DEFAULT_ERROR_MESSAGE = 'Could not upload file. The file may be invalid.';
function _fangornDropzoneError(tb, file, message) {
    // File may either be a webkit Entry or a file object, depending on the browser
    // On Chrome we can check if a directory is being uploaded
    var msgText;
    if (file.isDirectory) {
        msgText = 'Cannot upload directories, applications, or packages.';
    } else {
        msgText = DEFAULT_ERROR_MESSAGE;
    }
    var parent = file.treebeardParent || tb.dropzoneItemCache;
    // Parent may be undefined, e.g. in Chrome, where file is an entry object
    var item;
    var child;
    var destroyItem = false;
    for (var i = 0; i < parent.children.length; i++) {
        child = parent.children[i];
        if (!child.data.tmpID) {
            continue;
        }
        if (child.data.tmpID === file.tmpID) {
            item = child;
            tb.deleteNode(parent.id, item.id);
        }
    }
    $osf.growl('Error', msgText);
    tb.options.uploadInProgress = false;
    tb.options.iconState.generalIcons[1].on = false;
}

/**
 * Click event for when upload buttonin Action Column, it essentially runs the hiddenFileInput.click
 * @param event DOM event object for click
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} col Information pertinent to that column where this upload event is run from
 * @private
 */
function _uploadEvent(event, item, col) {
    var self = this;  // jshint ignore:line
    try {
        event.stopPropagation();
    } catch (e) {
        window.event.cancelBubble = true;
    }
    self.dropzoneItemCache = item;
    self.dropzone.hiddenFileInput.click();
    if (!item.open) {
        self.updateFolder(null, item);
    }
}

/**
 * Download button in Action Column
 * @param event DOM event object for click
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} col Information pertinent to that column where this upload event is run from
 * @private
 */
function _downloadEvent (event, item, col) {
    try {
        event.stopPropagation();
    } catch (e) {
        window.event.cancelBubble = true;
    }
    window.location = waterbutler.buildTreeBeardDownload(item);
}

/**
 * Deletes the item, only appears for items
 * @param event DOM event object for click
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} col Information pertinent to that column where this upload event is run from
 * @private
 */
function _removeEvent (event, item, col) {
    try {
        event.stopPropagation();
    } catch (e) {
        window.event.cancelBubble = true;
    }
    var tb = this;

    function cancelDelete() {
        this.modal.dismiss();
    }
    function runDelete() {
        var tb = this;
        $('.tb-modal-footer .btn-success').html('<i> Deleting...</i>').attr('disabled', 'disabled');
        // delete from server, if successful delete from view
        var url = resolveconfigOption.call(this, item, 'resolveDeleteUrl', [item]);
        url = url || waterbutler.buildTreeBeardDelete(item);
        $.ajax({
            url: url,
            type: 'DELETE'
        })
        .done(function(data) {
            // delete view
            tb.deleteNode(item.parentID, item.id);
            tb.modal.dismiss();
        })
        .fail(function(data){
            tb.modal.dismiss();
            item.notify.update('Delete failed.', 'danger', undefined, 3000);
        });
    }

    if (item.data.permissions.edit) {
        var mithrilContent = m('div', [
                m('h3.break-word', 'Delete "' + item.data.name+ '"?'),
                m('p', 'This action is irreversible.')
            ]);
        var mithrilButtons = m('div', [
                m('button', { 'class' : 'btn btn-default m-r-md', onclick : function() { cancelDelete.call(tb); } }, 'Cancel'),
                m('button', { 'class' : 'btn btn-success', onclick : function() { runDelete.call(tb); }  }, 'OK')
            ]);
        tb.modal.update(mithrilContent, mithrilButtons);
    } else {
        item.notify.update('You don\'t have permission to delete this file.', 'info', undefined, 3000);
    }
}

/**
 * Resolves lazy load url for fetching children
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {String|Boolean} Returns the fetch URL in string or false if there is no url.
 * @private
 */
function _fangornResolveLazyLoad(item) {
    var configOption = resolveconfigOption.call(this, item, 'lazyload', [item]);
    if (configOption) {
        return configOption;
    }

    if (item.data.provider === undefined) {
        return false;
    }
    return waterbutler.buildTreeBeardMetadata(item);
}

/**
 * Checks if the file being uploaded exists by comparing name of existing children with file name
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} file File object that dropzone passes
 * @this Treebeard.controller
 * @returns {boolean}
 * @private
 */
// function _fangornFileExists(item, file) {
//     var i,
//         child;
//     for (i = 0; i < item.children.length; i++) {
//         child = item.children[i];
//         if (child.kind === 'file' && child.data.name === file.name) {
//             return true;
//         }
//     }
//     return false;
// }

/**
 * Handles errors in lazyload fetching of items, usually link is wrong
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @private
 */
function _fangornLazyLoadError (item) {
    var configOption = resolveconfigOption.call(this, item, 'lazyLoadError', [item]);
    if (!configOption) {
        item.notify.update('Files couldn\'t load, please try again later.', 'deleting', undefined, 3000);
    }
}

/**
 * Applies the positionining and initialization of tooltips for file names
 * @private
 */
function reapplyTooltips () {
    $('[data-toggle="tooltip"]').tooltip({container: 'body'});
    $(".title-text [data-toggle=tooltip]").hover(function(event){
        var mousePosition = event.pageX - 20;
        $('.tooltip').css('left', mousePosition + 'px');
    });
}

/**
 * Called when new object data has arrived to be loaded.
 * @param {Object} tree A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @private
 */
function _fangornLazyLoadOnLoad (tree) {
    tree.children.forEach(function(item) {
        inheritFromParent(item, tree);
    });
    resolveconfigOption.call(this, tree, 'lazyLoadOnLoad', [tree]);
    reapplyTooltips();

    if (tree.depth > 1) {
        _fangornOrderFolder.call(this, tree);
    }
}

/**
 * Order contents of a folder without an entire sorting of all the table
 * @param {Object} tree A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @private
 */
function _fangornOrderFolder(tree) {
    var sortDirection = this.isSorted[1].desc ? 'desc' : 'asc';
    tree.sortChildren(this, sortDirection, 'text', 0);
    this.redraw();
}

/**
 * Changes the upload method based on what the add ons need. Default is POST, S3 needs PUT
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {string} Must return string that is a legitimate method like POST, PUT
 * @private
 */
function _fangornUploadMethod(item) {
    var configOption = resolveconfigOption.call(this, item, 'uploadMethod', [item]);
    return configOption || 'PUT';
}


/**
 * Defines the contents for the action column, upload and download buttons etc.
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} col Options for this particulat column
 * @this Treebeard.controller
 * @returns {Array} Returns an array of mithril template objects using m()
 * @private
 */
function _fangornDefineToolbar (item) {
    var self = this,
        buttons = [];
    // Upload button if this is a folder
    // If File and FileRead are not defined dropzone is not supported and neither is uploads
    if (window.File && window.FileReader && item.kind === 'folder' && item.data.provider && item.data.permissions.edit) {
        buttons.push({ name : 'uploadFiles', template : function(){
            return m('.fangorn-toolbar-icon.text-success', {
                    onclick : function(event) { _uploadEvent.call(self, event, item); } 
                },[
                m('i.fa.fa-upload'),
                m('span.hidden-xs','Upload')
            ]);
        } });
    }
    //Download button if this is an item
    if (item.kind === 'file') {
        buttons.push({ name : 'downloadSingle', template : function(){
            return m('.fangorn-toolbar-icon.text-primary', {
                    onclick : function(event) { _downloadEvent.call(self, event, item); }
                }, [
                m('i.fa.fa-download'),
                m('span.hidden-xs','Download')
            ]);
        }});
        if (item.data.permissions && item.data.permissions.edit) {
            buttons.push({ name : 'deleteSingle', template : function(){
                return m('.fangorn-toolbar-icon.text-danger', {
                        onclick : function(event) { _removeEvent.call(self, event, item); } 
                    }, [
                    m('i.fa.fa-times'),
                    m('span.hidden-xs','Delete')
                ]);
            }});
        }
    }
    item.icons = buttons;
}

/**
 * Defines the contents of the title column (does not include the toggle and folder sections
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} col Options for this particulat column
 * @this Treebeard.controller
 * @returns {Array} Returns an array of mithril template objects using m()
 * @private
 */
function _fangornTitleColumn(item, col) {
    if (item.kind === 'file' && item.data.permissions.view) {
        return m('span',{
            onclick: function() {
                var redir = new URI(item.data.nodeUrl);
                redir.segment('files').segment(item.data.provider).segmentCoded(item.data.path.substring(1));
                window.location = redir.toString() + '/';
            },
            'data-toggle' : 'tooltip', title : 'View file', 'data-placement': 'bottom'
        }, item.data.name);
    }
    return m('span', item.data.name);
}

/**
 * Parent function for resolving rows, all columns are sub methods within this function
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {Array} An array of columns that get iterated through in Treebeard
 * @private
 */
function _fangornResolveRows(item) {
    var default_columns = [];
    var configOption;
    item.css = '';
    if(this.isMultiselected(item.id)){
        item.css = 'fangorn-selected';
    }
    // define the toolbar icons for this item
    _fangornDefineToolbar.call(this, item);
    if(item.data.tmpID){
        return [
        {
            data : 'name',  // Data field name
            folderIcons : true,
            filter : true,
            custom : function(){ return m('span.text-muted', item.data.name); }
        },
        {
            data : '',  // Data field name
            custom : function(){ return m('span.text-muted', [m('span','Upload pending...'), cancelUploadTemplate.call(this, item) ]); }
        },
        {
            data : '',  // Data field name
            custom : function(){ return m('span', ''); }
        }
        ];
    }

    if (item.parentID) {
        item.data.permissions = item.data.permissions || item.parent().data.permissions;
        if (item.data.kind === 'folder') {
            item.data.accept = item.data.accept || item.parent().data.accept;
        }
    }

    default_columns.push(
    {
        data : null,
        folderIcons: false,
        filter : false,
        custom : function(){
            if(this.isMultiselected(item.id)) {
                return m('div.fangorn-select-toggle', { style : 'color: white'},m('i.fa.fa-check-square-o'));
            }
            return m('div.fangorn-select-toggle', m('i.fa.fa-square-o'));
        }
    },{
        data : 'name',  // Data field name
        folderIcons : true,
        filter : true,
        custom : _fangornTitleColumn
    });
    if (item.data.provider === 'osfstorage' && item.data.kind === 'file') {
        default_columns.push({
            data : 'downloads',
            sortInclude : false,
            filter : false,
            custom: function() { return item.data.extra ? item.data.extra.downloads.toString() : ''; }
        });
    } else {
        default_columns.push({
            data : 'downloads',
            sortInclude : false,
            filter : false,
            custom : function() { return m(''); }
        });
    }
    configOption = resolveconfigOption.call(this, item, 'resolveRows', [item]);
    return configOption || default_columns;
}

/**
 * Defines Column Titles separately since content and css may be different, allows more flexibility
 * @returns {Array} an Array of column information that gets templated inside Treebeard
 * @this Treebeard.controller
 * @private
 */
function _fangornColumnTitles () {
    var columns = [];
    columns.push(
    {   
        title : '',
        width: '5%',
        sort: false
    },
    {
        title: 'Name',
        width : '85%',
        sort : true,
        sortType : 'text'
    }, {
        title : 'Downloads',
        width : '10%',
        sort : false
    });
    return columns;
}

/**
 * When fangorn loads the top level needs to be open so we load the children on load
 * @this Treebeard.controller
 * @private
 */
function _loadTopLevelChildren() {
    var i;
    for (i = 0; i < this.treeData.children.length; i++) {
        this.updateFolder(null, this.treeData.children[i]);
    }
}

/**
 * Expand major addons on load
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @private
 */
function expandStateLoad(item) {
    var tb = this,
        i;
    if (item.children.length > 0 && item.depth === 1) {
        for (i = 0; i < item.children.length; i++) {
            // if (item.children[i].data.isAddonRoot || item.children[i].data.addonFullName === 'OSF Storage' ) {
                tb.updateFolder(null, item.children[i]);
            // }
        }
    }
    if (item.children.length > 0 && item.depth === 2) {
        for (i = 0; i < item.children.length; i++) {
            if (item.children[i].data.isAddonRoot || item.children[i].data.addonFullName === 'OSF Storage' ) {
                tb.updateFolder(null, item.children[i]);
            }
        }
    }
    reapplyTooltips();
}


function _fangornToolbar () {
    var tb = this;
    var titleContent = tb.options.title();
    if(tb.options.iconState.mode === 'bar'){                   
        return m('.row.tb-header-row', [
                m('.col-xs-12', [   
                        m('i.m-r-sm','Select rows for further actions.'),
                        m('.fangorn-toolbar.pull-right', 
                            [   
                                tb.options.iconState.rowIcons.map(function(icon){
                                    if(icon.template){
                                        return icon.template.call(tb);                                    
                                    }
                                }),
                                tb.options.iconState.generalIcons.map(function(icon){
                                    if(icon.on){
                                        return icon.template.call(tb);
                                    }
                                })
                            ]
                        )
                    ])
            ]);  
    }
    if(tb.options.iconState.mode === 'search'){
        return m('.row.tb-header-row', [
                m('', [
                        m('.col-xs-11',{ style : 'width: 90%'}, tb.options.filterTemplate.call(tb)),
                        m('.col-xs-1', 
                            m('.fangorn-toolbar.pull-right', 
                                toolbarDismissIcon.call(tb)
                            )
                        )
                    ])
            ]);  
    }    
} 

/** 
 * Toolbar icon templates 
 *
 */
function toolbarDismissIcon (){
    var tb = this;
    return m('.fangorn-toolbar-icon', {
            onclick : function () { tb.options.iconState.mode = 'bar'; tb.resetFilter(); }
        },
        m('i.fa.fa-times')
    );
}
 function searchIcon (){
    var tb = this;
    return m('.fangorn-toolbar-icon.text-info', { 
            onclick : function () { tb.options.iconState.mode = 'search'; }
        }, [
        m('i.fa.fa-search'),
        m('span.hidden-xs', 'Search')
    ]);
 }
 function cancelUploadsIcon (){
    var tb = this;
    return m('.fangorn-toolbar-icon.text-warning', { 
            onclick : function () { tb.options.iconState.mode = 'search'; }
        }, [
        m('i.fa.fa-times-circle'),
        m('span.hidden-xs', 'Cancel All Uploads')
    ]);
 }
 function deleteMultipleIcon (){
    var tb = this;
    return m('.fangorn-toolbar-icon.text-danger', { 
            onclick : function () { tb.options.iconState.mode = 'search'; }
        }, [
        m('i.fa.fa-trash'),
        m('span.hidden-xs', 'Delete Selected')
    ]);
 }




/**
 * OSF-specific Treebeard options common to all addons.
 * Check Treebeard API for more information
 */
tbOptions = {
    rowHeight : 30,         // user can override or get from .tb-row height
    showTotal : 15,         // Actually this is calculated with div height, not needed. NEEDS CHECKING
    paginate : false,       // Whether the applet starts with pagination or not.
    paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
    uploads : true,         // Turns dropzone on/off.
    columnTitles : _fangornColumnTitles,
    resolveRows : _fangornResolveRows,
    hoverClassMultiselect : 'fangorn-selected',
    multiselect : true,
    title : function() {
        if(window.contextVars.uploadInstruction) {
            // If File and FileRead are not defined dropzone is not supported and neither is uploads
            if (window.File && window.FileReader) {
                return m('p.p-xs.no-margin', [
                    m('span', 'Select rows for further actions (i.e. upload, delete) ')
                ]);
            }
            return m('p', {
                class: 'text-danger'
            }, [
                m('span', 'Your browser does not support file uploads, ', [
                    m('a', { href: 'http://browsehappy.com' }, 'learn more'),
                    '.'
                ])
            ]);
        }
        return undefined;
    },
    showFilter : true,     // Gives the option to filter by showing the filter box.
    allowMove : false,       // Turn moving on or off.
    hoverClass : 'fangorn-hover',
    togglecheck : _fangornToggleCheck,
    sortButtonSelector : {
        up : 'i.fa.fa-chevron-up',
        down : 'i.fa.fa-chevron-down'
    },
    onload : function () {
        var tb = this;
        _loadTopLevelChildren.call(tb);
        $(document).on('click', '.fangorn-dismiss', function() {
            tb.redraw();
        });

        $(window).on('beforeunload', function() {
            if (tb.dropzone && tb.dropzone.getUploadingFiles().length) {
              return 'You have pending uploads, if you leave this page they may not complete.';
            }
        });
    },
    createcheck : function (item, parent) {
        return true;
    },
    deletecheck : function (item) {  // When user attempts to delete a row, allows for checking permissions etc.
        return true;
    },
    movecheck : function (to, from) { //This method gives the users an option to do checks and define their return
        return true;
    },
    movefail : function (to, from) { //This method gives the users an option to do checks and define their return
        return true;
    },
    addcheck : function (treebeard, item, file) {
        var size;
        var maxSize;
        var displaySize;
        var msgText;
        if (_fangornCanDrop(treebeard, item)) {
            if (item.data.accept && item.data.accept.maxSize) {
                size = file.size / 1000000;
                maxSize = item.data.accept.maxSize;
                if (size > maxSize) {
                    displaySize = Math.round(file.size / 10000) / 100;
                    msgText = 'One of the files is too large (' + displaySize + ' MB). Max file size is ' + item.data.accept.maxSize + ' MB.';
                    item.notify.update(msgText, 'warning', undefined, 3000);
                    return false;
                }
            }
            return true;
        }
        return false;
    },
    onscrollcomplete : function(){
        reapplyTooltips();
    },
    onmultiselect : function(event, row) {
        var tb = this;
        event.preventDefault();
        this.options.iconState.rowIcons = [];
        if(tb.multiselected.length === 1){
            // empty row icons and assign row icons from item information
            this.options.iconState.rowIcons = row.icons;
            // temporarily remove classes until mithril redraws raws with another hover. 
            // $('.tb-row').removeClass('fangorn-selected');
            // $('.tb-row[data-id="' + row.id + '"]').removeClass(this.options.hoverClass).addClass('fangorn-selected');
            tb.select('#tb-tbody').removeClass('unselectable');
        } else {
            tb.select('#tb-tbody').addClass('unselectable');
        }
    },
    filterPlaceholder : 'Search',
    onmouseoverrow : _fangornMouseOverRow,
    sortDepth : 2,
    dropzone : {                                           // All dropzone options.
        url: function(files) {return files[0].url;},
        clickable : '#treeGrid',
        addRemoveLinks: false,
        previewTemplate: '<div></div>',
        parallelUploads: 1,
        acceptDirectories: false,
        fallback: function(){}
    },
    resolveIcon : _fangornResolveIcon,
    resolveToggle : _fangornResolveToggle,
    // Pass ``null`` to avoid overwriting Dropzone URL resolver
    resolveUploadUrl: function() {return null;},
    resolveLazyloadUrl : _fangornResolveLazyLoad,
    resolveUploadMethod: _fangornUploadMethod,
    lazyLoadError : _fangornLazyLoadError,
    lazyLoadOnLoad : _fangornLazyLoadOnLoad,
    ontogglefolder : expandStateLoad,
    dropzoneEvents : {
        uploadprogress : _fangornUploadProgress,
        sending : _fangornSending,
        complete : _fangornComplete,
        success : _fangornDropzoneSuccess,
        error : _fangornDropzoneError,
        dragover : _fangornDragOver,
        addedfile : _fangornAddedFile
    },
    resolveRefreshIcon : function() {
        return m('i.fa.fa-refresh.fa-spin');
    },
    removeIcon : function(){
        return m('i.fa.fa-times-circle');
    },
    headerTemplate : _fangornToolbar,
    // Not treebeard options, specific to Fangorn
    iconState : {
        mode : 'bar',
        generalIcons : [
            { name : 'search', on : true, template : searchIcon },
            { name : 'cancelUploads', on : false, template : cancelUploadsIcon },
            { name : 'deleteMultiple', on : false, template :  deleteMultipleIcon },
        ],
        rowIcons : [{}]

    },
    defineToolbar : _fangornDefineToolbar
};

/**
 * Loads Fangorn with options
 * @param {Object} options The options to be extended with Treebeard options
 * @constructor
 */
function Fangorn(options) {
    this.options = $.extend({}, tbOptions, options);
    this.grid = null;       // Set by _initGrid
    this.init();
}

/**
 * Initialize Fangorn methods that connect it to Treebeard
 * @type {{constructor: Fangorn, init: Function, _initGrid: Function}}
 */
Fangorn.prototype = {
    constructor: Fangorn,
    init: function () {
        this._initGrid();
    },
    // Create the Treebeard once all addons have been configured
    _initGrid: function () {
        this.grid = new Treebeard(this.options);
        return this.grid;
    }
};

Fangorn.ButtonEvents = {
    _downloadEvent: _downloadEvent,
    _uploadEvent: _uploadEvent,
    _removeEvent: _removeEvent
};

Fangorn.DefaultColumns = {
    _fangornTitleColumn: _fangornTitleColumn
};

Fangorn.Utils = {
    inheritFromParent: inheritFromParent,
    resolveconfigOption: resolveconfigOption,
    reapplyTooltips : reapplyTooltips
};

module.exports = Fangorn;
