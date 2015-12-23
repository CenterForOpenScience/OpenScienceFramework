/**
 * Created by cos-caner on 12/4/15.
 */

var logActions = {
    'project_created':  '${user} created ${node}',
    'project_registered': '${user} registered ${node}', // case : project_registered_no_user
    'project_deleted':  '${user} deleted ${node}',
    'created_from':     '${user} created ${node} based on ${template}',
    'pointer_created':  '${user} created a link to ${pointer}',
    'pointer_forked':   '${user} forked a link to ${pointer}',
    'pointer_removed':  '${user} removed a link to ${pointer}',
    'made_public':  '${user} made ${node} public', // case: made_public_no_user
    'made_private':     '${user} made ${node} private',
    'tag_added':    '${user} tagged ${node} as ${tag}',
    'tag_removed':  '${user} removed {$tag} from ${node}',
    'edit_title':   '${user} changed the title from ${title_original} to ${title_new}',
    'edit_description': '${user} edited description of ${node}',
    'updated_fields':   '${user} changed the ${updated_fields} for ${node}', // i.e change category
    'external_ids_added':   '${user} created external identifiers ${identifiers} on ${node}',
    'contributor_added':    '${user} added ${contributors} as contributor(s) to ${node}',
    'contributor_removed':  '${user} removed ${contributors} as contributor(s) from ${node}',
    'contributors_reordered':   '${user} reordered contributors for ${node}',
    'permissions_update':   '${user} changed permissions for ${node}',
    'made_contributor_visible':     '${user} made ${contributors} visible on ${node}',
    'made_contributor_invisible':   '${user} made ${contributors} invisible on ${node}',
    'wiki_updated':     '${user} updated wiki page ${page} to version ${version} of ${node}',
    'wiki_deleted':     '${user} deleted wiki page ${page} of ${node}',
    'wiki_renamed':     '${user} renamed wiki page ${old_page} to ${page} of ${node}',
    'made_wiki_public':     '${user} made the wiki of ${node} publicly editable',
    'made_wiki_private':    '${user} made the wiki of ${node} privately editable',
    'addon_added':  '${user} added addon ${addon} to ${node}',
    'addon_removed':    '${user} removed addon ${addon} from ${node}',
    'addon_file_moved':     '${user} copied ${source} to ${destination}',
    'addon_file_copied':    '${user} copied ${source} to ${destination}',
    'addon_file_renamed':   '${user} renamed ${source} to ${destination}',
    'folder_created':   '${user} created a folder in ${node}',
    'file_added':   '${user} added file ${path} to ${node}',
    'file_updated':     '${user} updated file in ${node}',
    'file_removed':     '$}user} removed file ${path} from ${node}',
    'file_restored':    '${user} restored file ${path} from ${node}',
    'comment_added':    '${user} added a comment to ${node}',
    'comment_removed':  '${user} deleted a comment from ${node}',
    'comment_updated':  '${user} updated a comment on ${node}',
    'embargo_initiated':    '${user} initiated an embargoed registration of ${node}',
    'embargo_approved':     '${user} approved embargoed registration of ${node}', // case where embargo_approved_no_user
    'embargo_cancelled':    '${user} cancelled embargoed registration of ${node}',
    'embargo_completed':    '${user} completed embargo of ${node}', // case embargo_completed_no_user
    'retraction_initiated':     'A Retraction of a Registration is proposed',
    'retraction_approved':  '${user} approved retraction of registration of ${node}',
    'retraction_cancelled':     '${user} cancelled retraction of registration of ${node}',
    'registration_initiated':   '${user} initiated retraction of registration of ${node}',
    'registration_approved':    '${user} approved registration of ${node}', // case: registration_approved_no_user
    'registration_cancelled':   '${user} cancelled registration of ${node}',
    'node_created':     '${user} created ${node}', // deprecated
    'node_forked':  '${user} created fork from ${node}', // deprecated
    'node_removed':  '${user} removed ${node}', // deprecated
    'license_changed' : '${user} updated the license of ${node}',
    'osf_storage_file_added' : '${user} added ${path} to OSF Storage in ${node}',
    'osf_storage_folder_created' : '${user} created folder ${path} in OSF Storage in ${node}',
    'osf_storage_file_updated' : '${user} updated file ${path} in OSF Storage in ${node}',
    'osf_storage_file_removed' : '${user} removed ${path} from OSF Storage in ${node}'
};

module.exports = logActions;