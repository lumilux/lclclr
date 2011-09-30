function colorToHex(_red, _green, _blue) {
        var red = parseInt(_red);
            var green = parseInt(_green);
                var blue = parseInt(_blue);
                    var rgb = blue | (green << 8) | (red << 16);
                        return digits[1] + '#' + rgb.toString(16);
};
jQuery(document).ready(function($){
	if (navigator.geolocation) {
		navigator.geolocation.getCurrentPosition(
			function (position) {
				jQuery.ajaxSetup({ scriptCharset: "utf-8" , contentType: "application/json; charset=utf-8"});
				jQuery("body").css("background-image", 'url("http://maps.google.com/maps/api/staticmap?center='+position.coords.latitude+','+position.coords.longitude+'&zoom=16&size=600x600&maptype=roadmap&sensor=true")');
				var response = jQuery.getJSON(
			        "http://lclclr.com/fl/"+position.coords.latitude+"/"+position.coords.longitude, function(data) {
			            var items = [];
			            jQuery.each(data, function(key, val) {
			                items.push('<li id="' + key + '"><a href="'+val[3]+'" class="color" style="background-color:rgb('+parseInt(val[0], 10)+','+parseInt(val[1],10)+','+parseInt(val[2],10)+')"></a></li>');//<img src="' + val + '" /></li>');
			            });
			            jQuery(".results").replaceWith(jQuery('<ul/>', {
			                'class': 'results',
			                html: items.join('')
			            }));
			    });
			},
			function (error) {
				jQuery(".results").append("<strong>"+error.code+"</strong>");
			}
		);
	}
});

