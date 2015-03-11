/**
 * Usage:
 *
 *  var Animal = defclass({
 *      constructor: function(name) {
 *          this.name = name || 'unnamed';
 *          this.sleeping = false;
 *      },
 *      sayHi: function() {
 *          console.log('Hi, my name is ' + this.name);
 *      }
 *  });
 */
function defclass(prototype) {
    var constructor = prototype.constructor;
    constructor.prototype = prototype;
    return constructor;
}

/**
 * Usage:
 *
 *     var Person = extend(Animal, {
 *         constructor: function(name) {
 *             this.super.constructor(name);
 *             this.name = name || 'Steve';
 *         }
 *     });
 */
function extend(constructor, sub) {
    var prototype = Object.create(constructor.prototype);
    for (var key in sub) { prototype[key] = sub[key]; }
    prototype.super = constructor.prototype;
    return defclass(prototype);
}

module.exports = {
    defclass: defclass,
    extend: extend
};
