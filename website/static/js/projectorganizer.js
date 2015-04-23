/**
 * Handles Project Organizer on dashboard page of OSF.
 * For Treebeard and _item API's check: https://github.com/caneruguz/treebeard/wiki
 */
'use strict';

var Treebeard = require('treebeard');

// CSS
require('css/typeahead.css');
require('css/fangorn.css');
require('css/projectorganizer.css');

var Handlebars = require('handlebars');
var $ = require('jquery');
var m = require('mithril');
var bootbox = require('bootbox');
var Bloodhound = require('exports?Bloodhound!typeahead.js');
var moment = require('moment');
var Raven = require('raven-js');


var $osf = require('./osfHelpers');

// copyMode can be 'copy', 'move', 'forbidden', or null.
// This is set at draglogic and is used as global within this module
var copyMode = null;
// Initialize projectOrganizer object (separate from the ProjectOrganizer constructor at the end)
var projectOrganizer = {};

// Link ID's used to add existing project to folder
    var linkName;
    var linkID;

// Cross browser key codes for the Command key
var commandKeys = [224, 17, 91, 93]; 

/**
 * Bloodhound is a typeahead suggestion engine. Searches here for public projects
 * @type {Bloodhound}
 */
projectOrganizer.publicProjects = new Bloodhound({
    datumTokenizer: function (d) {
        return Bloodhound.tokenizers.whitespace(d.name);
    },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    remote: {
        url: '/api/v1/search/projects/?term=%QUERY&maxResults=20&includePublic=yes&includeContributed=no',
        filter: function (projects) {
            return $.map(projects, function (project) {
                return {
                    name: project.value,
                    node_id: project.id,
                    category: project.category
                };
            });
        },
        limit: 10
    }
});

/**
 * Bloodhound is a typeahead suggestion engine. Searches here for users projects
 * @type {Bloodhound}
 */
projectOrganizer.myProjects = new Bloodhound({
    datumTokenizer: function (d) {
        return Bloodhound.tokenizers.whitespace(d.name);
    },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    remote: {
        url: '/api/v1/search/projects/?term=%QUERY&maxResults=20&includePublic=no&includeContributed=yes',
        filter: function (projects) {
            return $.map(projects, function (project) {
                return {
                    name: project.value,
                    node_id: project.id,
                    category: project.category
                };
            });
        },
        limit: 10
    }
});

/**
 * Edits the template for the column titles.
 * Used here to make smart folder italicized
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller Check Treebeard API for methods available
 * @private
 */
function _poTitleColumn(item) {
    var tb = this;
    var css = item.data.isSmartFolder ? 'project-smart-folder smart-folder' : '';
    return m('span', { 'class' : css , ondblclick : function(event){ 
            if(commandKeys.indexOf(tb.pressedKey) !== -1) {
                window.open(item.data.urls.fetch, '_blank');
            } else {
                window.open(item.data.urls.fetch, '_self');
            }
        }
    }, item.data.name);
}

/**
 * Links for going to project pages on the action column
 * @param event Click event
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} col Column options
 * @this Treebeard.controller Check Treebeard API for methods available
 * @private
 */
function _gotoEvent(event, item) {
    var tb = this; 
    if(commandKeys.indexOf(tb.pressedKey) !== -1) {
        window.open(item.data.urls.fetch, '_blank');
    } else {
        window.open(item.data.urls.fetch, '_self');
    }

}


/**
 * Watching for escape key press
 * @param {String} nodeID Unique ID of the node
 */
function addFormKeyBindings(nodeID) {
    $('#ptd-' + nodeID).keyup(function (e) {
        if (e.which === 27) {
            $('#ptd-' + nodeID).find('.cancel-button-' + nodeID).filter(':visible').click();
            return false;
        }
    });
}


function triggerClickOnItem(item, force) {
    var row = $('.tb-row[data-id="'+ item.id+'"]');
    if (force){
        row.trigger('click');
    }

    if(row.hasClass(this.options.hoverClassMultiselect)){
        row.trigger('click');
    }
}

/**
 * Saves the expand state of a folder so that it can be loaded based on that state
 * @param {Object} item Node data
 * @param {Function} callback
 */
function saveExpandState(item, callback) {
    var collapseUrl,
        postAction,
        expandUrl;
    if (!item.apiURL) {
        return;
    }
    if (item.expand) {
        // turn to false
        collapseUrl = item.apiURL + 'collapse/';
        postAction = $osf.postJSON(collapseUrl, {});
        postAction.done(function () {
            item.expand = false;
            if (typeof callback !== 'undefined') {
                callback();
            }
        }).fail($osf.handleJSONError);
    } else {
        // turn to true
        expandUrl = item.apiURL + 'expand/';
        postAction = $osf.postJSON(expandUrl, {});
        postAction.done(function () {
            item.expand = false;
            if (typeof callback !== 'undefined') {
                callback();
            }
        }).fail($osf.handleJSONError);
    }
}

/**
 * Contributors have first person's name and then number of contributors. This functio nreturns the proper html
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @returns {Object} A Mithril virtual DOM template object
 * @private
 */
function _poContributors(item) {
    if (!item.data.contributors) {
        return '';
    }

    return item.data.contributors.map(function (person, index, arr) {
        var comma;
        if(index === 0) {
            comma = '';
        } else {
            comma = ', ';
        }
        if (index > 2) {
            return;
        }
        if (index === 2) {
            return m('span', ' + ' + (arr.length - 2));
        }
        return m('span', comma + person.name );
    });
}

/**
 * Displays who modified the data and when. i.e. "6 days ago, by Uguz"
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @private
 */
function _poModified(item) {
    var personString = '';
    var dateString = '';
    if (item.data.modifiedDelta === 0) {
        return m('span');
    }
    dateString = moment.utc(item.data.dateModified).fromNow();
    if (item.data.modifiedBy !== '') {
        personString = ', by ' + item.data.modifiedBy.toString();
    }
    return m('span', dateString + personString);
}

/**
 * Organizes all the row displays based on what that item requires.
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @returns {Array} An array of columns as col objects
 * @this Treebeard.controller Check Treebeard API For available methods
 * @private
 */
function _poResolveRows(item) {
    var css = '',
        draggable = false,
        default_columns;
    if (item.data.permissions) {
        draggable = item.data.permissions.movable || item.data.permissions.copyable;
    }
    if (draggable) {
        css = 'po-draggable';
    }
    // define the toolbar icons for this item
    _poDefineToolbar.call(this, item);

    item.css = '';
    default_columns = [{
        data : 'name',  // Data field name
        folderIcons : true,
        filter : true,
        css : css,
        custom : _poTitleColumn
    }, {
        filter : false,
        custom : _poContributors
    }, {
        filter : false,
        custom : _poModified
    }];
    return default_columns;
}

/**
 * Organizes the information for Column title row.
 * @returns {Array} An array of columns with pertinent column information
 * @private
 */
function _poColumnTitles() {
    var columns = [];
    columns.push({
        title: 'Name',
        width : '50%',
        sort : false
    }, {
        title : 'Contributors',
        width : '25%',
        sort : false
    }, {
        title : 'Modified',
        width : '25%',
        sort : false
    });
    return columns;
}

/**
 * Checks if folder toggle is permitted (i.e. contents are private)
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {boolean}
 * @private
 */
function _poToggleCheck(item) {
    if (item.data.permissions.view) {
        return true;
    }
    item.notify.update('Not allowed: Private folder', 'warning', 1, undefined);
    return false;
}

/**
 * Returns custom icons for OSF depending on the type of item
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {Object}  Returns a mithril template with the m() function.
 * @private
 */
function _poResolveIcon(item) {
    var viewLink,
        icons = {
            folder : 'fa-cubes',
            smartFolder : 'fa-certificate',
            project : 'fa-cube',
            registration :  'fa-th-list text-muted',
            component :  'fa-th-large',
            registeredComponent :  'fa-th-large text-muted',
            link :  'fa-link'
        };
    viewLink = item.data.urls.fetch;
    function returnView(type) {
        var template = m('.fa', { 'class' : icons[type]});
        if (viewLink) {
            return m('a', { href : viewLink}, template);
        }
        return template;
    }
    if (item.data.isSmartFolder) {
        return returnView('smartFolder');
    }
    if (item.data.isFolder) {
        return returnView('folder');
    }
    if(item.data.isPointer && !item.parent().data.isFolder){
        return returnView('link');
    }
    if (item.data.isProject) {
        if (item.data.isRegistration) {
            return returnView('registration');
        } else {
            return returnView('project');
        }
    }

    if (item.data.isComponent) {
        if (item.data.isRegistration) {
            return returnView('registeredComponent');
        }else {
            return returnView('component');
        }
    }

    if (item.data.isPointer) {
        return returnView('link');
    }
    return returnView('folder');
}

/**
 * Returns custom folder toggle icons for OSF
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {string} Returns a mithril template with m() function, or empty string.
 * @private
 */
function _poResolveToggle(item) {
    var toggleMinus = m('i.fa.fa-minus'),
        togglePlus = m('i.fa.fa-plus'),
        childrenCount = item.data.childrenCount || item.children.length;
    if (item.kind === 'folder' && childrenCount > 0 && item.depth > 1) {
        if (item.open) {
            return toggleMinus;
        }
        return togglePlus;
    }
    return '';
}

/**
 * Resolves lazy load url for fetching children
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {String|Boolean} Returns the fetch URL in string or false if there is no url.
 * @private
 */
function _poResolveLazyLoad(item) {

    return '/api/v1/dashboard/' + item.data.node_id;
}

/**
 * Hook to run after lazyloading has successfully loaded
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @private
 */
function expandStateLoad(item) {
    var tb = this,
        i;
    if(item.children.length === 0 && item.data.childrenCount > 0){
        item.data.childrenCount = 0;
        tb.updateFolder(null, item);
    }
    if (item.children.length > 0 && item.depth > 0) {
        for (i = 0; i < item.children.length; i++) {
            if (item.children[i].data.expand) {
                tb.updateFolder(null, item.children[i]);
            }
            if(tb.multiselected[0] && item.children[i].data.node_id === tb.multiselected[0].data.node_id) {
                triggerClickOnItem.call(tb, item.children[i], true);
            }
        }
    }
    _cleanupMithril();
}

/**
 * Loads the children of an item that need to be expanded. Unique to Projectorganizer
 * @private
 */
function _poLoadOpenChildren() {
    var tb = this;
    this.treeData.children.map(function (item) {
        if (item.data.expand) {
            tb.updateFolder(null, item);
        }
    });
}

/**
 * Hook to run after multiselect is run when an item is selected.
 * @param event Browser click event object
 * @param {Object} tree A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @private
 */
function _poMultiselect(event, tree) {
    $('.tb-header-row .twitter-typeahead').remove();
    var tb = this,
        selectedRows = filterRowsNotInParent.call(tb, tb.multiselected),
        someItemsAreFolders,
        pointerIds;
    tb.options.iconState.rowIcons = [];
    if(!tb.filterOn){
        tb.options.iconState.mode = 'bar';
    }
    if(tb.multiselected.length === 1){
        // empty row icons and assign row icons from item information
        tb.options.iconState.rowIcons = tree.icons;
        //tb.options.iconState.title = tree.data.name;

        // temporarily remove classes until mithril redraws raws with another hover. 
        tb.select('#tb-tbody').removeClass('unselectable');
    } else {
        tb.select('#tb-tbody').addClass('unselectable');

       someItemsAreFolders = false;
        pointerIds = [];
        selectedRows.forEach(function (item) {
            var thisItem = item.data;
            someItemsAreFolders = someItemsAreFolders ||
                                  thisItem.isFolder ||
                                  thisItem.isSmartFolder ||
                                  thisItem.parentIsSmartFolder ||
                                  !thisItem.permissions.movable;
            pointerIds.push(thisItem.node_id);
        });
        var detailTemplateContext;
        if(!selectedRows[0].parent().data.isFolder){
            // detailTemplateContext = {
            //     itemsCount: selectedRows.length
            // };
            // var theParentNode = selectedRows[0].parent();
            // var displayHTML = multiItemDetailTemplateNoAction(detailTemplateContext);
            // $detailDiv.html(displayHTML).show();
        } else {
            if (!someItemsAreFolders) {
                // detailTemplateContext = {
                //     multipleItems: true,
                //     itemsCount: selectedRows.length
                // };
                // var theParentNode = selectedRows[0].parent();
                // var displayHTML = multiItemDetailTemplate(detailTemplateContext);
                // $detailDiv.html(displayHTML).show();
                // $('#remove-links-multiple').click(function () {
                //     deleteMultiplePointersFromFolder.call(tb, pointerIds, theParentNode);
                //     createBlankProjectDetail();
                // });
                // $('#close-multi-select').click(function () {
                //     createBlankProjectDetail();
                //     return false;
                // });
            } else {
                // detailTemplateContext = {
                //     itemsCount: selectedRows.length
                // };
                // var theParentNode = selectedRows[0].parent();
                // var displayHTML = multiItemDetailTemplateNoAction(detailTemplateContext);
                // $detailDiv.html(displayHTML).show();
            }
        }



    }

}



/**
 * Deletes pointers based on their ids from the folder specified
 * @param {String} pointerIds Unique node ids
 * @param folderToDeleteFrom  What it says
 */
function deleteMultiplePointersFromFolder(pointerIds, folderToDeleteFrom) {
    var tb = this,
        folderNodeId,
        url,
        postData,
        deleteAction;
    if (pointerIds.length > 0) {
        folderNodeId = folderToDeleteFrom.data.node_id;
        url = '/api/v1/folder/' + folderNodeId + '/pointers/';
        postData = JSON.stringify({pointerIds: pointerIds});
        deleteAction = $.ajax({
            type: 'DELETE',
            url: url,
            data: postData,
            contentType: 'application/json',
            dataType: 'json'
        });
        deleteAction.done(function () {
            tb.updateFolder(null, folderToDeleteFrom);
        });
        deleteAction.fail(function (jqxhr, textStatus, errorThrown) {
            $osf.growl('Error:', textStatus + '. ' + errorThrown);
        });
    }
}

/**
 * When multiple rows are selected remove those that are not in the parent
 * @param {Array} rows List of item objects
 * @returns {Array} newRows Returns the revised list of rows
 */
function filterRowsNotInParent(rows) {
    if (this.multiselected.length < 2) {
        return this.multiselected;
    }
    var i, newRows = [],
        originalRow = this.find(this.multiselected[0].id),
        originalParent,
        currentItem;
    if (typeof originalRow !== "undefined") {
        originalParent = originalRow.parentID;
        for (i = 0; i < rows.length; i++) {
            currentItem = rows[i];
            if (currentItem.parentID === originalParent && currentItem.id !== -1) {
                newRows.push(rows[i]);
            }
        }
    }
    this.multiselected = newRows;
    this.highlightMultiselect();
    return newRows;
}

/**
 * Hook for the drag start event on jquery
 * @param event jQuery UI drggable event object
 * @param ui jQuery UI draggable ui object
 * @private
 */
function _poDragStart(event, ui) {
    var itemID = $(event.target).attr('data-id'),
        item = this.find(itemID);
    if (this.multiselected.length < 2) {
        this.multiselected = [item];
    }
}

/**
 * Hook for the drop event of jQuery UI droppable
 * @param event jQuery UI droppable event object
 * @param ui jQuery UI droppable ui object
 * @private
 */
function _poDrop(event, ui) {
    var items = this.multiselected.length === 0 ? [this.find(this.selected)] : this.multiselected,
        folder = this.find($(event.target).attr('data-id'));
    dropLogic.call(this, event, items, folder);
}

/**
 * Hook for the over event of jQuery UI droppable
 * @param event jQuery UI droppable event object
 * @param ui jQuery UI droppable ui object
 * @private
 */
function _poOver(event, ui) {
    var items = this.multiselected.length === 0 ? [this.find(this.selected)] : this.multiselected,
        folder = this.find($(event.target).attr('data-id')),
        dragState = dragLogic.call(this, event, items, ui);
    $('.tb-row').removeClass('tb-h-success po-hover');
    if (dragState !== 'forbidden') {
        $('.tb-row[data-id="' + folder.id + '"]').addClass('tb-h-success');
    } else {
        $('.tb-row[data-id="' + folder.id + '"]').addClass('po-hover');
    }
}

// Sets the state of the alt key by listening for key presses in the document.
var altKey = false;
$(document).keydown(function (e) {
    if (e.altKey) {
        altKey = true;
    }
});
$(document).keyup(function (e) {
    if (!e.altKey) {
        altKey = false;
    }
});

/**
 * Sets the copy state based on which item is being dragged on which other item
 * @param {Object} event Browser drag event
 * @param {Array} items List of items being dragged at the time. Each item is a _item object
 * @param {Object} ui jQuery UI draggable drag ui object
 * @returns {String} copyMode One of the copy states, from 'copy', 'move', 'forbidden'
 */
function dragLogic(event, items, ui) {
    var canCopy = true,
        canMove = true,
        folder = this.find($(event.target).attr('data-id')),
        isSelf = false,
        dragGhost = $('.tb-drag-ghost');
    items.forEach(function (item) {
        if (!isSelf) {
            isSelf = item.id === folder.id;
        }
        canCopy = canCopy && item.data.permissions.copyable;
        canMove = canMove && item.data.permissions.movable;
    });
    if (canAcceptDrop(items, folder) && (canMove || canCopy)) {
        if (canMove && canCopy) {
            if (altKey) {
                copyMode = 'copy';
            } else {
                copyMode = 'move';
            }
        }
        if (canMove && !canCopy) {
            copyMode = 'move';
        }
        if (canCopy && !canMove) {
            copyMode = 'copy';
        }
    } else {
        copyMode = 'forbidden';
    }
    if (isSelf) {
        copyMode = 'forbidden';
    }
    // Set the cursor to match the appropriate copy mode
    // Remember that Treebeard is using tb-drag-ghost instead of ui.helper

    switch (copyMode) {
    case 'forbidden':
        dragGhost.css('cursor', 'not-allowed');
        break;
    case 'copy':
        dragGhost.css('cursor', 'copy');
        break;
    case 'move':
        dragGhost.css('cursor', 'move');
        break;
    default:
        dragGhost.css('cursor', 'default');
    }
    return copyMode;
}

/**
 * Checks if the folder can accept the items dropped on it
 * @param {Array} items List of items being dragged at the time. Each item is a _item object
 * @param {Object} folder Folder information as _item object, the drop target
 * @returns {boolean} canDrop Whether drop can happen
 */
function canAcceptDrop(items, folder, theCopyMode) {
    if(typeof theCopyMode === 'undefined'){
        theCopyMode = copyMode;
    }
    var representativeItem,
        itemParentNodeId,
        hasComponents,
        hasFolders,
        copyable,
        movable,
        canDrop;
    if (folder.data.isSmartFolder || !folder.data.isFolder) {
        return false;
    }
    // if the folder is contained by the item, return false
    representativeItem = items[0];
    if (representativeItem.isAncestor(folder) || representativeItem.id === folder.id) {
        return false;
    }
    // If trying to drop on the folder it came from originally, return false
    itemParentNodeId = representativeItem.parent().data.node_id;
    if (itemParentNodeId === folder.data.node_id) {
        return false;
    }
    hasComponents = false;
    hasFolders = false;
    copyable = true;
    movable = true;
    canDrop = true;
    items.forEach(function (item) {
        hasComponents = hasComponents || item.data.isComponent;
        hasFolders = hasFolders || item.data.isFolder;
        copyable = copyable && item.data.permissions.copyable;
        movable = movable && item.data.permissions.movable;
    });
    if (hasComponents) {
        canDrop = canDrop && folder.data.permissions.acceptsComponents;
    }
    if (hasFolders) {
        canDrop = canDrop && folder.data.permissions.acceptsFolders;
    }
    if (theCopyMode === 'move') {
        canDrop = canDrop && folder.data.permissions.acceptsMoves && movable;
    }
    if (theCopyMode === 'copy') {
        canDrop = canDrop && folder.data.permissions.acceptsCopies && copyable;
    }
    return canDrop;
}

/**
 * Where the drop actions happen
 * @param event jQuery UI drop event
 * @param {Array} items List of items being dragged at the time. Each item is a _item object
 * @param {Object} folder Folder information as _item object
 */
function dropLogic(event, items, folder) {
    var tb = this,
        theFolderNodeID,
        getChildrenURL,
        folderChildren,
        sampleItem,
        itemParent,
        itemParentNodeID,
        getAction;
    if (typeof folder !== 'undefined' && !folder.data.isSmartFolder && folder !== null && folder.data.isFolder) {
        theFolderNodeID = folder.data.node_id;
        getChildrenURL = folder.data.apiURL + 'get_folder_pointers/';
        sampleItem = items[0];
        itemParent = sampleItem.parent();
        itemParentNodeID = itemParent.data.node_id;
        if (itemParentNodeID !== theFolderNodeID) { // This shouldn't happen, but if it does, it's bad
            getAction = $.getJSON(getChildrenURL, function (data) {
                folderChildren = data;
                var itemsToMove = [],
                    itemsNotToMove = [],
                    postInfo;
                items.forEach(function (item) {
                    if ($.inArray(item.data.node_id, folderChildren) === -1) { // pointer not in folder to be moved to
                        itemsToMove.push(item.data.node_id);
                    } else if (copyMode === 'move') { // Pointer is already in the folder and it's a move
                                // We  need to make sure not to delete the folder if the item is moved to the same folder.
                                // When we add the ability to reorganize within a folder, this will have to change.
                        itemsNotToMove.push(item.data.node_id);
                    }
                });
                postInfo = {
                    'copy': {
                        'url': '/api/v1/project/' + theFolderNodeID + '/pointer/',
                        'json': {
                            nodeIds: itemsToMove
                        }
                    },
                    'move': {
                        'url': '/api/v1/pointers/move/',
                        'json': {
                            pointerIds: itemsToMove,
                            toNodeId: theFolderNodeID,
                            fromNodeId: itemParentNodeID
                        }
                    }
                };
                if (copyMode === 'copy' || copyMode === 'move') {
                    deleteMultiplePointersFromFolder.call(tb, itemsNotToMove, itemParent);
                    if (itemsToMove.length > 0) {
                        var url = postInfo[copyMode]['url'],
                            postData = JSON.stringify(postInfo[copyMode]['json']),
                            outerFolder = whichIsContainer.call(tb, itemParent, folder),
                            postAction = $.ajax({
                                type: 'POST',
                                url: url,
                                data: postData,
                                contentType: 'application/json',
                                dataType: 'json'
                            });
                        postAction.always(function (result) {
                            if (copyMode === 'move') {
                                if (!outerFolder) {
                                    tb.updateFolder(null, itemParent);
                                    tb.updateFolder(null, folder);
                                } else {
                                    // if item is closed folder save expand state to be open
                                    if(!folder.data.expand){
                                        saveExpandState(folder.data, function(){
                                            tb.updateFolder(null, outerFolder);
                                        });
                                    } else {
                                        tb.updateFolder(null, outerFolder);
                                    }
                                }
                            } else {
                                tb.updateFolder(null, folder);
                            }
                        });
                        postAction.fail(function (jqxhr, textStatus, errorThrown) {
                            $osf.growl('Error:', textStatus + '. ' + errorThrown);
                        });
                    }
                }
            });
            getAction.fail(function (jqxhr, textStatus, errorThrown) {
                $osf.growl('Error:', textStatus + '. ' + errorThrown);
            });
        } else {
            Raven.captureMessage('Project dashboard: Parent node (' + itemParentNodeID + ') == Folder Node (' + theFolderNodeID + ')');
        }
    } else {
        if (typeof folder === 'undefined') {
            Raven.captureMessage('onDrop folder is undefined.');
        }
    }
    $('.project-organizer-dand').css('cursor', 'default');
}

/**
 * Checks if one of the items being moved contains the other. To check for adding parents to children
 * @param {Object} itemOne Treebeard _item object, has the _item API
 * @param {Object} itemTwo Treebeard _item object, has the _item API
 * @returns {null|Object} Returns object if one is containing the other. Null if neither or both
 */
function whichIsContainer(itemOne, itemTwo) {
    var isOneAncestor = itemOne.isAncestor(itemTwo),
        isTwoAncestor = itemTwo.isAncestor(itemOne);
    if (isOneAncestor && isTwoAncestor) {
        return null;
    }
    if (isOneAncestor) {
        return itemOne;
    }
    if (isTwoAncestor) {
        return itemTwo;
    }
    return null;
}

function _cleanupMithril() {
    // Clean up Mithril related redraw issues
    $('.tb-toggle-icon').each(function(){
        var children = $(this).children('i');
        if (children.length > 1) {
            children.last().remove();
        }
    });
}

/** 
 * Toolbar icon templates and click functions 
 *
 */

 function _toolbarDismissEvent ( ){
    var tb = this;
    $('.tb-header-row .twitter-typeahead').remove();
    tb.options.iconState.mode = 'bar'; 
    tb.resetFilter();
    tb.filterText(''); 
 }

function toolbarDismissIcon (){
    var tb = this;
    return m('.fangorn-toolbar-icon', {
            onclick : function () { 
                _toolbarDismissEvent.call(tb);
            }
        },
        m('i.fa.fa-times')
    );
}
 function searchButton (){
    var tb = this;
    return m('.fangorn-toolbar-icon.text-info', { 
            'data-toggle' : 'tooltip',
            'title':  'Switch to search panel to filter rows below.',
            'data-placement' : 'bottom',
            onclick : function () { tb.options.iconState.mode = 'search'; }
        }, [
        m('i.fa.fa-search'),
        m('span.hidden-xs', 'Search')
    ]);
 }
 
 function _addFolderEvent () {
    var tb = this;
    var val = $.trim($('#addNewFolder').val());
    if(tb.multiselected.length !== 1 || val.length < 1){
        tb.options.iconState.mode = 'bar'; 
        return; 
    }
    var item = tb.multiselected[0];
    var theItem = item.data;
    var url = '/api/v1/folder/',
    postData = {
        node_id: theItem.node_id,
        title: val
    };
    theItem.expand = false;
    saveExpandState(theItem, function () {
        var putAction = $osf.putJSON(url, postData);
        putAction.done(function () {
            tb.updateFolder(null, item);
            triggerClickOnItem.call(tb, item);
        }).fail($osf.handleJSONError);

    });
    tb.options.iconState.mode = 'bar'; 
 }

 function addFolderButton (){
    var tb = this;
    return m('.fangorn-toolbar-icon.text-info', { 
            onclick : function () { 
                _addFolderEvent.call(tb);
            }
        }, [
        m('i.fa.fa-plus'),
        m('span.hidden-xs', 'Add')
    ]);
 }

function _renameEvent () {
    var tb = this;
    var val = $.trim($('#renameInput').val());
    if(tb.multiselected.length !== 1 || val.length < 1){
        tb.options.iconState.mode = 'bar'; 
        return; 
    }
    var item = tb.multiselected[0];
    var theItem = item.data;
    var url = theItem.apiURL + 'edit/',
        postAction,
        postData = {
            name: 'title',
            value: val
        };
    postAction = $osf.postJSON(url, postData);
    postAction.done(function () {
        tb.updateFolder(null, tb.find(1));
        // Also update every
    }).fail($osf.handleJSONError);
    tb.options.iconState.mode = 'bar'; 
}

 function renameButton (){
    var tb = this;
    return m('.fangorn-toolbar-icon.text-info', { 
            onclick : function () { 
                _renameEvent.call(tb);
            }
        }, [
        m('i.fa.fa-pencil'),
        m('span.hidden-xs', 'Rename')
    ]);
 }


function applyTypeahead () {
    var tb = this;
    var item = tb.multiselected[0];
    var theItem = item.data;
    projectOrganizer.myProjects.initialize();
    projectOrganizer.publicProjects.initialize();
    // injecting error into search results from https://github.com/twitter/typeahead.js/issues/747
    var mySourceWithEmptySelectable = function (q, cb) {
        var emptyMyProjects = [{ error: 'There are no matching projects to which you contribute.' }];
        projectOrganizer.myProjects.get(q, injectEmptySelectable);
        function injectEmptySelectable(suggestions) {
            if (suggestions.length === 0) {
                cb(emptyMyProjects);
            } else {
                cb(suggestions);
            }
        }
    };
    var publicSourceWithEmptySelectable = function (q, cb) {
        var emptyPublicProjects = { error: 'There are no matching public projects.' };
        projectOrganizer.publicProjects.get(q, injectEmptySelectable);
        function injectEmptySelectable(suggestions) {
            if (suggestions.length === 0) {
                cb([emptyPublicProjects]);
            } else {
                cb(suggestions);
            }
        }
    };


    if (!theItem.isSmartFolder) {
        $('#addprojectInput').typeahead('destroy');
        $('#addprojectInput').typeahead({
            highlight: true
        }, {
            name: 'my-projects',
            displayKey: function (data) {
                return data.name;
            },
            source: mySourceWithEmptySelectable,
            templates: {
                header: function () {
                    return '<h3 class="category">My Projects</h3>';
                },
                suggestion: function (data) {
                    if (typeof data.name !== 'undefined') {
                        return '<p>' + data.name + '</p>';
                    }
                    return '<p>' + data.error + '</p>';
                }
            }
        }, {
            name: 'public-projects',
            displayKey: function (data) {
                return data.name;
            },
            source: publicSourceWithEmptySelectable,
            templates: {
                header: function () {
                    return '<h3 class="category">Public Projects</h3>';
                },
                suggestion: function (data) {
                    if (typeof data.name !== 'undefined') {
                        return '<p>' + data.name + '</p>';
                    }
                    return '<p>' + data.error + '</p>';
                }
            }
        });
        $('#addprojectInput').bind('keyup', function (event) {
            var key = event.keyCode || event.which,
                buttonEnabled = $('#add-link-button').hasClass('tb-disabled');

            if (key === 13) {
                if (buttonEnabled) {
                    $('#add-link-button').click(); //submits if the control is active
                }
            } else {
                $('#add-link-warning').text('');
                $('#add-link-button').addClass('tb-disabled');
                linkName = '';
                linkID = '';
            }
        });
        $('#addprojectInput').bind('typeahead:selected', function (obj, datum, name) {
            var getChildrenURL = theItem.apiURL + 'get_folder_pointers/',
                children;
            $.getJSON(getChildrenURL, function (data) {
                children = data;
                if (children.indexOf(datum.node_id) === -1) {
                    $('#add-link-button').removeClass('tb-disabled');
                    linkName = datum.name;
                    linkID = datum.node_id;
                } else {
                    $('#add-link-warning').text('This project is already in the folder');
                }
            }).fail($osf.handleJSONError);
        });
    }

}

 function addProjectButton (){
    var tb = this;
    var item = tb.multiselected[0];
    var theItem = item.data;

    return m('#add-link-button.fangorn-toolbar-icon.text-info.tb-disabled', {
            onclick : function () { 

            var url = '/api/v1/pointer/',
                postData = JSON.stringify({
                    pointerID: linkID,
                    toNodeID: theItem.node_id
                });
            theItem.expand = false;
            saveExpandState(theItem, function () {
                var postAction = $.ajax({
                        type: 'POST',
                        url: url,
                        data: postData,
                        contentType: 'application/json',
                        dataType: 'json'
                    });
                postAction.done(function () {
                    tb.updateFolder(null, item);
                });
            });
            triggerClickOnItem.call(tb, item);
            tb.options.iconState.mode = 'bar';
            }
        }, [
        m('i.fa.fa-plus'),
        m('span.hidden-xs', 'Add')
    ]);
 }


function _poToolbar (){
    var tb = this; 
    var generalButtons = [];
    var generalIcons = tb.options.iconState.generalIcons;
    if (generalIcons.search.on) { 
        generalButtons.push(generalIcons.search.template.call(tb));
    }
    if (tb.options.iconState.mode === 'bar'){                   
        return m('.row.tb-header-row', [
                m('.col-xs-12.tb-buttons-col', [   
                        m('.fangorn-toolbar.pull-right', 
                            [   
                                tb.options.iconState.rowIcons.map(function(icon){
                                    if(icon.template){
                                        return icon.template.call(tb);                                    
                                    }
                                }),
                                generalButtons
                            ]
                        )
                    ])
            ]);  
    }
    if(tb.options.iconState.mode === 'search'){
        return m('.row.tb-header-row', [
                m('', [
                        m('.col-xs-11', tb.options.filterTemplate.call(tb)),
                        m('.col-xs-1.tb-buttons-col', 
                            m('.fangorn-toolbar.pull-right', 
                                toolbarDismissIcon.call(tb)
                            )
                        )
                    ])
            ]);  
    }
    if(tb.options.iconState.mode === 'addFolder'){
        return m('.row.tb-header-row', [
                m('', [
                        m('.col-xs-9', m('input#addNewFolder.tb-header-input', { 'placeholder' : 'Collection name'})),
                        m('.col-xs-3.tb-buttons-col', 
                            m('.fangorn-toolbar.pull-right', 
                                [
                                addFolderButton.call(tb),
                                toolbarDismissIcon.call(tb)
                                ]
                            )
                        )
                    ])
            ]);  
    }    
    if(tb.options.iconState.mode === 'rename'){
        return m('.row.tb-header-row', [
                m('', [
                        m('.col-xs-9', m('input#renameInput.tb-header-input', { value : tb.multiselected[0].data.name })),
                        m('.col-xs-3.tb-buttons-col', 
                            m('.fangorn-toolbar.pull-right', 
                                [
                                renameButton.call(tb),
                                toolbarDismissIcon.call(tb)
                                ]
                            )
                        )
                    ])
            ]);  
    }
    if(tb.options.iconState.mode === 'addProject'){
        return m('.row.tb-header-row', [
                m('', [
                        m('.col-xs-9', [
                                m('input#addprojectInput.tb-header-input', { config : function(){ applyTypeahead.call(tb);}, type : 'text', placeholder : 'Name of the project to find'}),
                                m('#add-link-warning.text-warning.p-sm')
                            ]
                        ),
                        m('.col-xs-3.tb-buttons-col', 
                            m('.fangorn-toolbar.pull-right', 
                                [
                                addProjectButton.call(tb),
                                toolbarDismissIcon.call(tb)
                                ]
                            )
                        )
                    ])
            ]);  
    }   

} 

function _poDefineToolbar (item){
    var tb = this; 
    var buttons = [];
    var url = item.data.urls.fetch;
    var theItem = item.data;
    var theParentNode = item.parent();
    var theParentNodeID = theParentNode.data.node_id;
    $('[data-toggle="tooltip"]').tooltip('destroy');

    if (!item.data.isSmartFolder) {
        if (url !== null) {
            buttons.push(
            { name : 'gotoEvent', template : function(){
                return m('.fangorn-toolbar-icon.text-primary', {
                    'data-toggle' : 'tooltip',
                    'title':  'Opens the project in same window. Use Command + Click to open in new window.',
                    'data-placement' : 'bottom',
                        onclick : function(event) { _gotoEvent.call(tb, event, item); }
                    }, [
                    m('i.fa.fa-external-link'),
                    m('span.hidden-xs','Open')
                ]);
            }}
            );
        }
    }

    if(!item.data.isSmartFolder && (item.data.isDashboard || item.data.isFolder) ) {
        buttons.push(
        { name : 'addFolder', template : function(){
            return m('.fangorn-toolbar-icon.text-primary', {
                    'data-toggle' : 'tooltip',
                    'title':  'Adds a Collection to visually organize your projects or components.',
                    'data-placement' : 'bottom',
                    onclick : function(event) {  
                        tb.options.iconState.mode = 'addFolder';
                    }
                }, [
                m('i.fa.fa-cubes'),
                m('span','Add Collection')
            ]);
        }},
        { name : 'addExistingProject', template : function(){
            return m('.fangorn-toolbar-icon.text-primary', {
                    'data-toggle' : 'tooltip',
                    'title':  'Adds an existing project or component to the Collection.',
                    'data-placement' : 'bottom',
                    onclick : function(event) {
                        tb.options.iconState.mode = 'addProject';
                    }
                }, [
                m('i.fa.fa-cube'),
                m('span','Add Existing Project')
            ]);
        }}
        );
    }
    if(!item.data.isFolder && item.data.parentIsFolder && !item.parent().data.isSmartFolder) {
        buttons.push(
        { name : 'removeFromFolder', template : function(){
            return m('.fangorn-toolbar-icon.text-primary', {
                    'data-toggle' : 'tooltip',
                    'title':  'Removes the selected row from the Collection. This action does NOT delete the project.',
                    'data-placement' : 'bottom',
                    onclick : function(event) {  
                        var url = '/api/v1/folder/' + theParentNodeID + '/pointer/' + theItem.node_id,
                            deleteAction = $.ajax({
                                type: 'DELETE',
                                url: url,
                                contentType: 'application/json',
                                dataType: 'json'
                            });
                        deleteAction.done(function () {
                            tb.updateFolder(null, theParentNode);

                        });
                    }
                }, [
                m('i.fa.fa-minus'),
                m('span','Remove From Folder')
            ]);
        }}
        );
    }
    if(!item.data.isDashboard && !item.data.isRegistration && item.data.permissions && item.data.permissions.edit){
        buttons.push(
        { name : 'renameItem', template : function(){
            return m('.fangorn-toolbar-icon.text-primary', {
                    'data-toggle' : 'tooltip',
                    'title':  'Change the name of the Collection or project',
                    'data-placement' : 'bottom',
                    onclick : function(event) {  
                        tb.options.iconState.mode = 'rename';
                    }
                }, [
                m('i.fa.fa-font'),
                m('span','Rename')
            ]);
        }}
        );
    }
    if(item.data.isFolder && !item.data.isDashboard && !item.data.isSmartFolder){
        buttons.push(
        { name : 'deleteFolder', template : function(){
            return m('#deleteFolder.fangorn-toolbar-icon.text-primary', {
                    'data-toggle' : 'tooltip',
                    'title':  'Deletes a collection.',
                    'data-placement' : 'bottom',
                    onclick : function(event) {  
                        _deleteFolder.call(tb, item, theItem);
                    }
                }, [
                m('i.fa.fa-trash'),
                m('span','Delete Collection')
            ]);
        }}
        );
    }


   item.icons = buttons;
}

function _deleteFolder (item) {
    var tb = this;
    var theItem = item.data;
    bootbox.confirm({
        title: 'Delete this folder?',
        message: 'Are you sure you want to delete this Collection? This will also delete any Collections ' +
            'inside this one. You will not delete any projects in this Collection.',
        callback: function (result) {
            if (result !== null && result) {
                var url = '/api/v1/folder/' + theItem.node_id,
                    deleteAction = $.ajax({
                        type: 'DELETE',
                        url: url,
                        contentType: 'application/json',
                        dataType: 'json'
                    });
                deleteAction.done(function () {
                    tb.updateFolder(null, item.parent());
                });
            }
        }
    });
}

//
/**
 * OSF-specific Treebeard options common to all addons.
 * For documentation visit: https://github.com/caneruguz/treebeard/wiki
 */
var tbOptions = {
    rowHeight : 27,         // user can override or get from .tb-row height
    showTotal : 15,         // Actually this is calculated with div height, not needed. NEEDS CHECKING
    paginate : false,       // Whether the applet starts with pagination or not.
    paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
    uploads : false,         // Turns dropzone on/off.
    columnTitles : _poColumnTitles,
    resolveRows : _poResolveRows,
    showFilter : true,     // Gives the option to filter by showing the filter box.
    title : false,          // Title of the grid, boolean, string OR function that returns a string.
    allowMove : true,       // Turn moving on or off.
    moveClass : 'po-draggable',
    hoverClass : 'fangorn-hover',
    hoverClassMultiselect : 'fangorn-selected',
    togglecheck : _poToggleCheck,
    sortButtonSelector : {
        up : 'i.fa.fa-chevron-up',
        down : 'i.fa.fa-chevron-down'
    },
    dragOptions : {},
    dropOptions : {},
    dragEvents : {
        start : _poDragStart
    },
    dropEvents : {
        drop : _poDrop,
        over : _poOver
    },
    onload : function () {
        var tb = this,
            rowDiv = $('.tb-row');
        _poLoadOpenChildren.call(tb);
       rowDiv.first().trigger('click');

        $('.gridWrapper').on('mouseout', function(){
            rowDiv.removeClass('po-hover');
        });
        $(document).on('keypress', '#renameInput', function(){
            if(tb.pressedKey === 13) {
                _renameEvent.call(tb);
            }
        });
        $(document).on('keypress', '#addNewFolder', function(){
            if(tb.pressedKey === 13) {
                _addFolderEvent.call(tb);
            }
        });
    },
    createcheck : function (item, parent) {
        return true;
    },
    deletecheck : function (item) {
        return true;
    },
    ontogglefolder : function (item, event) {
        if (event) {
            saveExpandState(item.data);
        }
        if (!item.open) {
            item.load = false;
        }
        $('[data-toggle="tooltip"]').tooltip();
    },
    onscrollcomplete : function(){
        $('[data-toggle="tooltip"]').tooltip();
        _cleanupMithril();
    },
    onmultiselect : _poMultiselect,
    resolveIcon : _poResolveIcon,
    resolveToggle : _poResolveToggle,
    resolveLazyloadUrl : _poResolveLazyLoad,
    lazyLoadOnLoad : expandStateLoad,
    resolveRefreshIcon : function() {
        return m('i.fa.fa-refresh.fa-spin');
    },
    headerTemplate : _poToolbar,
    // Not treebeard options, specific to Fangorn
    iconState : {
        mode : 'bar',
        generalIcons : {
            search : { on : true, template : searchButton }         
        },
        rowIcons : [{}]
        },
    defineToolbar : _poDefineToolbar,
    onselectrow : function(row) {
        console.log(row);
    }
};

/**
 * Initialize Project organizer in the fashion of Fangorn. Prepeares an option object within ProjectOrganizer
 * @param options Treebeard type options to be extended with Treebeard default options.
 * @constructor
 */
function ProjectOrganizer(options) {
    this.options = $.extend({}, tbOptions, options);
    this.grid = null; // Set by _initGrid
    this.init();
}

/**
 * Project organizer prototype object with init functions set to Treebeard.
 * @type {{constructor: ProjectOrganizer, init: Function, _initGrid: Function}}
 */
ProjectOrganizer.prototype = {
    constructor: ProjectOrganizer,
    init: function () {
        this._initGrid();
    },
    _initGrid: function () {
        this.grid = new Treebeard(this.options);
        return this.grid;
    }
};

module.exports = {
    ProjectOrganizer: ProjectOrganizer,
    _whichIsContainer: whichIsContainer,
    _canAcceptDrop: canAcceptDrop
};
