var lclclr = {
    colorToHex: function (rgb) {
        rgb = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
        function hex(x) {
            return ("0" + parseInt(x, 10).toString(16)).slice(-2);
        }
        return "0x" + hex(rgb[1]) + hex(rgb[2]) + hex(rgb[3]);
    }
};
$(document).ready(function($) {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                $.ajaxSetup({scriptCharset: "utf-8",contentType: "application/json; charset=utf-8"});
                var response = $.getJSON("http://lclclr.com/fl/" + position.coords.latitude + "/" + position.coords.longitude, function(data) {
                    var items = [];
                    var markers = [];
                    $.each(data.colors, function(key, val) {
                        var rgbColor = "rgb("+parseInt(val[0], 10)+","+parseInt(val[1], 10)+","+parseInt(val[2], 10)+")"
                        items.push('<li id="' + key + '"><a href="' + val[3] + '" class="color" style="background-color:' + rgbColor + '"></a></li>');
                        markers.push('&markers=color:' + lclclr.colorToHex(rgbColor) + '%7C' + val[4][0] + ',' + val[4][1]);
                    });
                    $(".results").replaceWith($('<ul/>', {
                        'class': 'results',
                        html: items.slice(0,5).join('')
                    }));
                    //$("body").css("background-image", 'url("http://maps.google.com/maps/api/staticmap?center=' + position.coords.latitude + ',' + position.coords.longitude + '&zoom=16&size=600x600&maptype=roadmap&sensor=true")');
                    $("html").css("background-color", "rgb(" + data.mean[0] + "," + data.mean[1] + "," + data.mean[2] + ")");
                    $(".results").css("background-image", 'url("http://maps.google.com/maps/api/staticmap?size=480x480&center=' + position.coords.latitude + ',' + position.coords.longitude + '&maptype=roadmap' + markers.join('') + '&sensor=true")');
                });
            },
            function(error) {
                $(".results").replaceWith($('<ul class="results"><strong>' + error.code + '</strong></ul>'));
            });
        }
});

