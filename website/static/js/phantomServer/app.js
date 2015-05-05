var express = require('express');
var phantom = require('phantom');
var app = express();

app.get('/', function (req, res) {

    var url = req.query.url;
    console.log(url);
    console.log(req.query);


    phantom.create(function(ph){

           // Adding cookies to authorize the user/node
//           ph.addCookie('osf', req.query.cookie, 'localhost', function (added) {
//                console.log('cookies added?', added);
//           });

           ph.createPage(function (page) {

               page.open(url, function (status) {
                   if (status == 'success') {
                       console.log("Success");

//                       page.getCookies(function(cookie){
//                           console.log(cookie);
//                       });

                       page.evaluate(
                           function () {
                               return document.documentElement.outerHTML;
                           },
                           function (content) {
//                             console.log(content);
                               res.send(content);
                               console.log('RESPONSE SEND');
                               ph.exit();
                           });
                   }
                   else {
                       console.log("Status Failed");
                       ph.exit();
                   }
               })

           });
////       }
//        else{
//            console.log("Cookies not added");
//            ph.exit();
//        }
    });

});

var server = app.listen(3000, function () {

  var host = server.address().address;
  var port = server.address().port;

  console.log('Example app listening at http://%s:%s', host, port);

});