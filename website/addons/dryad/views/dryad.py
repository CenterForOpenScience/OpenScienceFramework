# This should be the browser for dryad

from website.addons.dryad import api

import httplib
import logging
import datetime
import browser

from flask import request
from framework.flask import redirect

from framework.exceptions import HTTPError
from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon, must_be_valid_project
from website.project.views.node import _view_project

from website.addons.dryad.api import Dryad_DataOne

logger = logging.getLogger(__name__)

import xml.etree.ElementTree as ET

@must_be_valid_project
@must_have_addon('wiki', 'node')
def dryad_page(**kwargs):
    node = kwargs['node'] or kwargs['project']
    auth=kwargs['auth']
    


    count=40
    start=0
    try:
        count = int(request.args["count"])
    except Exception:
        count=40
    try:
        start = int(request.args["start"] )
    except Exception:
        start=0


    dryad = node.get_addon('dryad')
    

    d = Dryad_DataOne()
    x = d.list(count=count, start_n=start)
    count = int(x.getElementsByTagName("d1:objectList")[0].attributes["count"].value )
    start = int(x.getElementsByTagName("d1:objectList")[0].attributes["start"].value)
    total = int(x.getElementsByTagName("d1:objectList")[0].attributes["total"].value)

    ret = {"end": start+count,
            "start": start,
            "total":total,
            "content": "" }
    #Now to create the browser tree

    objectList = ET.Element("ul")

    for obj in x.getElementsByTagName("objectInfo"):
        ident = obj.getElementsByTagName("identifier")[0].firstChild.wholeText
        size = obj.getElementsByTagName("size")[0].firstChild.wholeText
        doi = "doi:"+ident.split("dx.doi.org/")[1].split("?")[0]
        
        objInfo = ET.SubElement(objectList, "li")
        objInfo.text = doi
        
        meta = d.metadata(doi)
        objInfo.text = meta.toprettyxml()
        title = meta.getElementsByTagName("dcterms:title")[0].firstChild.wholeText
        authors = "Authors:"+", ".join([ i.firstChild.wholeText for i in meta.getElementsByTagName("dcterms:creator")])
        objInfo.text = title

        sublist = ET.SubElement(objInfo,"ul")

        authorel = ET.SubElement(sublist, "p")
        authorel.text = authors

        authorel = ET.SubElement(sublist, "p")
        authorel.text = "Identifier:"+ident
        #now create the addon that will add this to the project

    ret.update({"content": ET.tostring(objectList)})
    ret.update(dryad.config.to_json() )
    ret.update(_view_project(node, auth, primary=True)) 

    return ret
    #return redirect(node.web_url_for('dryad_browser', wname='home', _guid=True))
    #return redirect(node.web_url_for('project_wiki_view', wname='home', _guid=True))
