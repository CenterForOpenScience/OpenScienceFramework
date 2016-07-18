var m = require('mithril');
var $osf = require('js/osfHelpers');
var waterbutler = require('js/waterbutler');
var AddProject = require('js/addProjectPlugin');
var dzPreviewTemplate = require('js/home-page/dropzonePreviewTemplate');

require('css/dropzone-plugin.css');
require('css/quick-project-search-plugin.css');
require('loaders.css/loaders.min.css');

var Dropzone = require('dropzone');
var Fangorn = require('js/fangorn');


// Don't show dropped content if user drags outside dropzone
window.ondragover = function (e) {
    e.preventDefault();
};
window.ondrop = function (e) {
    e.preventDefault();
};

var PublicFilesDropzone = {
    controller: function () {
        Dropzone.options.publicFilesDropzone = {
            // Dropzone is setup to upload multiple files in one request this configuration forces it to do upload file-by-
            //file, one request at a time.
            clickable: '#publicFilesDropzone',
            // prevents default uploading; call processQueue() to upload
            autoProcessQueue: false,
            withCredentials: true,
            method: 'put',
            maxFiles: 3,
            maxFilesize: 500,
            init: function () {
                // When user clicks close button on top right, reset the number of files
                var _this = this;
                $('button.close').on('click', function () {
                    _this.files = [];
                });

            },
            accept: function (file, done) {
                this.options.url = waterbutler.buildUploadUrl(false, 'osfstorage', window.contextVars.publicFilesId, file, {});

                if (this.files.length <= this.options.maxFiles) {
                    $('div.h2.text-center.m-t-lg').hide();
                }
                else {
                    if(!$('.alert-danger').length){

                        $osf.softGrowl('This feature is for sharing files, if you would like to store a many files for ' +
                        'a collaborative work or large presentation consider creating a project, this will give you access' +
                        ' to a large array of features and services', 'warning', 30000);

                        $( "#createNewProjectBtn" ).effect("highlight", {}, 3000);

                    }
                }
                this.processFile(file);
            },
            addedfile: function(file) {
                var node, removeFileEvent, removeLink, _i, _j, _k, _len, _len1, _len2, _ref, _ref1, _ref2, _results,
                _this = this;
                if (this.element === this.previewsContainer) {
                  this.element.classList.add('dz-started');
                }
                file.previewElement = Dropzone.createElement(this.options.previewTemplate.trim());
                file.previewTemplate = file.previewElement;
                this.previewsContainer.appendChild(file.previewElement);
                _ref = file.previewElement.querySelectorAll('[data-dz-name]');
                for (_i = 0, _len = _ref.length; _i < _len; _i++) {
                  node = _ref[_i];
                  node.textContent = file.name;
                }
                _ref1 = file.previewElement.querySelectorAll('[data-dz-size]');
                for (_j = 0, _len1 = _ref1.length; _j < _len1; _j++) {
                  node = _ref1[_j];
                  node.innerHTML = this.filesize(file.size);
                }
                if (this.options.addRemoveLinks) {
                  file._removeLink = Dropzone.createElement('<a class=\'dz-remove\' href=\'javascript:undefined;\' data-dz-remove>' + this.options.dictRemoveFile + '</a>');
                  file.previewElement.appendChild(file._removeLink);
                }
                removeFileEvent = function(e) {
                  e.preventDefault();
                  e.stopPropagation();
                  if (file.status === Dropzone.UPLOADING) {
                    return _this.removeFile(file);
                  } else {
                    if (_this.options.dictRemoveFileConfirmation) {
                      return Dropzone.confirm(_this.options.dictRemoveFileConfirmation, function() {
                        return _this.removeFile(file);
                      });
                    } else {
                      return _this.removeFile(file);
                    }
                  }
                };
                _ref2 = file.previewElement.querySelectorAll('[data-dz-remove]');
                _results = [];
                for (_k = 0, _len2 = _ref2.length; _k < _len2; _k++) {
                  removeLink = _ref2[_k];
                  _results.push(removeLink.addEventListener('click', removeFileEvent));
                }
                return _results;
            },
            sending: function (file, xhr) {
                this.options.url = waterbutler.buildUploadUrl(false, 'osfstorage', window.contextVars.publicFilesId, file, {});
                //Hack to remove webkitheaders
                var _send = xhr.send;
                xhr.send = function () {
                    _send.call(xhr, file);
                };
                $('.panel-body').append(file.previewElement);
                var iconSpan = document.createElement('span');
                $('div.dz-center').prepend(iconSpan);
                m.render(iconSpan, dzPreviewTemplate.resolveIcon(file));
            },
            success: function (file, xhr) {
                var buttonContainer = document.createElement('div');
                $(file.previewElement).find('div.col-sm-6').append(buttonContainer);
                var response = JSON.parse(file.xhr.response);
                var guid = '';

                $osf.ajaxJSON(
                    'GET',
                    $osf.apiV2Url('files' + response.path + '/',{ query : {'giveGuid': 1 }}),
                    {
                        isCors: true
                    }
                ).done(function(response) {
                    guid = response.data.attributes.guid;
                    var link = location.protocol+ '//' + location.host + '/' + guid;
                    m.render(buttonContainer, dzPreviewTemplate.shareButton(link));
                    $('.logo-spin').remove();
                    $('span.p-md').remove();
                    $('span.button.close').css('visibility', 'hidden');
                    file.previewElement.classList.add('dz-success');
                    file.previewElement.classList.add('dz-preview-background-success');
                    $(file.previewElement).find('.dz-filename').attr('href', guid);
                    if($('.alert-danger').length){
                        $( "#createNewProjectBtn" ).effect("highlight", {}, 3000);
                    }

                }).fail(function(xhr, status, error) {
                    $('.logo-spin').remove();
                    $('span.p-md').remove();
                    console.log(xhr);
                    console.log(status);
                    console.log(error);
                });

                $('div.dz-progress').remove();

                this.files.pop();
                this.processQueue();

            },
            canceled: function (file) {
                $osf.softGrowl('fa fa-files-o', ' Upload Canceled', 'info');

            },
            error: function (file, message) {
                this.files.pop();
                file.previewElement.remove(); // Doesn't show the preview
                // Need the padding change twice because the padding doesn't resize when there is an error
                // get file size in MB, rounded to 1 decimal place
                var fileSizeMB = Math.round(file.size / (this.options.filesizeBase * this.options.filesizeBase) * 10) / 10;
                if (fileSizeMB > this.options.maxFilesize) {
                    $osf.growl('Upload Failed', file.name + ' could not be uploaded. <br> The file is ' + fileSizeMB + ' MB,' +
                        ' which exceeds the max file size of ' + this.options.maxFilesize + ' MB', 'danger', 5000);
                }
            },

        };
        var $publicFiles = $('#publicFilesDropzone');

        $publicFiles.on('click', 'span.dz-share', function (e) {
            if (!$('.alert-info').length) {
                $osf.softGrowl('Link copied to clipboard', 'info', 20000 ,'fa fa-files-o');
            }
        });

        $publicFiles.dropzone({
            url: 'placeholder',
            previewTemplate: $osf.mithrilToStr(dzPreviewTemplate.dropzonePreviewTemplate())
        });
        $publicFiles.hide();

        $('#ShareButton').click(function () {
                $publicFiles.stop().slideToggle();
                $('#glyphchevron').toggleClass('fa fa-chevron-down fa fa-chevron-up');
            }
        );

    },

    view: function (ctrl, args) {
        function headerTemplate() {
            return [
                m('h2.col-xs-6', 'Dashboard'),
                m('m-b-lg.pull-right',
                    m('button.btn.btn-primary.m-t-md.m-r-sm.f-w-xl #ShareButton',
                        'Upload Public Files ', m('span.fa.fa-chevron-down #glyphchevron')
                    ),
                    m.component(AddProject, {
                            buttonTemplate: m('button.btn.btn-success.btn-success-high-contrast.m-t-md.f-w-xl.pull-right[data-toggle="modal"][data-target="#addProjectFromHome"] #createNewProjectBtn',
                                {
                                    onclick: function () {
                                        $osf.trackClick('quickSearch', 'add-project', 'open-add-project-modal');
                                    }
                                }, 'Create new project'),
                            modalID: 'addProjectFromHome',
                            stayCallback: function _stayCallback_inPanel() {
                                document.location.reload(true);
                        },
                        trackingCategory: 'quickSearch',
                        trackingAction: 'add-project',
                        templatesFetcher: ctrl.templateNodes
                        }
                    )
                )
            ];
        }

        function closeButton() {
            return [
                m('button.close.fa.fa-times.dz-font[aria-label="Close"].pull-right', {
                        onclick: function () {
                            $('#publicFilesDropzone').hide();
                            $('div.dz-preview').remove();
                            $('#glyphchevron').toggleClass('fa fa-chevron-up fa fa-chevron-down');
                        }
                    }
                )
            ];
        }

        function publicFilesHelpButton() {
            return [
                m('button.btn.fa.fa-info.close.dz-font[aria-label="Drag-and-Drop Help"][data-toggle="modal"][data-target="#dropZoneHelpModal"]'),
                m('.modal.fade.dz-cursor-default #dropZoneHelpModal',
                    m('.modal-dialog',
                        m('.modal-content',
                            m('.modal-header',
                                m('button.close[data-dismiss="modal"]', '×'),
                                m('h4.modal-title', 'Public Files Drag-and-Drop Help')),
                            m('.modal-body', m('p', 'Files uploaded here will be automatically added to your public files. Additionally: '),
                                m('ul',
                                    m('li', 'You may upload one file at a time.'),
                                    m('li', 'File uploads may be up to 256 MB.'),
                                    m('li', 'To upload more files, refresh the page or click ', m('span.i.fa.fa-times')),
                                    m('li', 'To show and hide your uploads, toggle the ', m('strong', 'Upload Public Files'), ' button.'),
                                    m('li', 'Click ', m('span.i.fa.fa-share-alt'), ' to copy a download link for that file to your clipboard. Share this link with others!'))
                            ),
                            m('.modal-footer', m('button.btn.btn-default[data-dismiss="modal"]', 'Close'))
                        )
                    )
                )
            ];
        }

        function publicFilesHeader() {
            return [
                m('a.btn.btn-primary.btn-success-high-contrasts.f-w-xl',
                    {href: '/public_files/'},
                 'Your Public Files')
            ];
        }

        // Activate Public Files tooltip info
        $('[data-toggle="tooltip"]').tooltip();
        return m('.row',
            m('.col-xs-12', headerTemplate()
            ),
            m('div.drop-zone-format.panel .panel-default #publicFilesDropzone',
                m('.panel-heading', closeButton(),
                    publicFilesHelpButton(), publicFilesHeader()
                ),
                m('.panel-body.dz-body-height', m('div.h2.text-center.m-t-lg.dz-bold #splashDropText', 'Drop a file to upload'),
                    m('span#dz-dragmessage.fa.fa-plus-square-o.fa-5x.dz-dragmessage', '')
                ),
                m('.panel-footer.dz-cursor-default.clearfix',
                    m('.pull-left',
                        m('h5', 'Files are uploaded to your ',
                            m('a', { href: '/public_files/' },
                             'Public Files'), ' ', m('i.fa.fa-question-circle.text-muted', {
                                'data-toggle': 'tooltip',
                                'title': 'The Public Files Project allows you to easily collaborate and share your files with anybody.',
                                'data-placement': 'bottom'
                            }, '')
                        )
                    ),
                    m('.pull-right',
                        m('button.btn.btn-success.m-r-sm #publicFilesDropzone', 'Choose a file'),
                        m('button.btn.btn-default', {
                            onclick: function () {
                                $('#publicFilesDropzone').hide();
                                $('div.dz-preview').remove();
                                $('#glyphchevron').toggleClass('fa fa-chevron-up fa fa-chevron-down');
                            }
                        }, 'Done')
                    )
                )
            )
        );
    }
};


module.exports = PublicFilesDropzone;