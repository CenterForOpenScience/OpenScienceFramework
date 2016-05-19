'use strict';

var $ = require('jquery');
var MathJax = require('MathJax');


/**
 * Render math with MathJax within a given element.
 * */
function mathjaxify(selector) {
    var $elem = $(selector);
    function typesetStubbornMath() {
        $elem.each(function() {
            if ($(this).text() !== '') {
                MathJax.Hub.Queue(['Typeset', MathJax.Hub, $(this).attr('id')]);
            }
        });
    }
    var preview = $elem[0];
    if (typeof(window.typeset) === 'undefined' || window.typeset === true) {
        MathJax.Hub.Queue(['Typeset', MathJax.Hub, preview]);
        typesetStubbornMath();
    }
}

// Helper function takes an element node and typesets its math markup.
// This can now be mapped over a nodelist or the like.
function typeset(el) {

    console.log("Typesetting elements...");  
 
    // If our element is not an element node, it can't have an id,
    // and so MathJax cannot process it. Let's return from the funciton early.                  
    if (el.nodeType !== 1) {
        console.log("not a node."); 
        return false;
    }
    // Make sure we're doing this in a browser...
    // This isn't _really_ a good enough guard against this getting 
    // run on the server, but hopefully we don't define window...
    console.log(window);
    console.log(typeof window);
    if (typeof window === "undefined") return;
        
    console.log("queueing element to typesetter")
    // Add an element by its id to MAthJax Queue to typeset.
    // As soon as MathJax has a queue, it'll start typesetting.
    window.MathJax.Hub.Queue(["Typeset", MathJax.Hub, el]);

}


module.exports = {
    mathjaxify: mathjaxify,
    typeset: typeset
};
