<%inherit file="project/project_base.mako"/>
<%def name="title()">Retract Registration of Component</%def>

<legend class="text-center">Retract Registration</legend>

    <div id="registrationRetraction" class="col-md-6 col-md-offset-3">
        <div class="panel panel-default">
            <div class="panel-body">
                Retracting a registration will remove its content from the OSF, but leave basic meta-data behind.
                The title of a retracted registration and its contributor list will remain, as will justification or
                explanation of the retraction, should you wish to provide it. Retracted registrations will be marked
                with a "retracted" tag. <strong>This action is irreversible.</strong>
            </div>
        </div>
        <form id="registration_retraction_form" role="form">

            <div class="form-group">
                <label class="control-label">Please provide your justification for retracting this registration.</label>
                <textarea
                        class="form-control"
                        data-bind="textInput: justification"
                        id="justificationInput"
                        autofocus
                        >
                </textarea>
            </div>

            <hr />

            <div class="form-group">
                <label class="control-label">Type '<span data-bind="text: registrationTitle"></span>' if you are sure you want to continue.</label>
                <textarea
                        class="form-control"
                        data-bind="textInput: confirmationText"
                        >
                </textarea>
            </div>
            <button type="submit" class="btn btn-danger" data-bind="click: submit, visible: true">Retract Registration</button>

        </form>
    </div>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script src="${'/static/public/js/registration-retraction-page.js' | webpack_asset}"></script>
</%def>