var pad = function (num, size) {
	var s = "0000000" + num;
	return s.substr(s.length-size);
}

{% if not login %}
var _check_running = function() {
	url = '{{ url_for("backup_running") }}';
	$.getJSON(url, function(data) {
		if (data.results) {
			$('#toblink').addClass('blink');
		} else {
			$('#toblink').removeClass('blink');
		}
	});
};
{% endif %}

/***
 * _clients_bh: Bloodhound object used for the autocompletion of the input field
 */
var _clients_bh = new Bloodhound({	
	datumTokenizer: Bloodhound.tokenizers.obj.whitespace('name'),
	queryTokenizer: Bloodhound.tokenizers.whitespace,
	limit: 10,
	prefetch: {
		url: '{{ url_for("clients") }}',
		filter: function(list) {
			return list.results;
		}
	}
});

_clients_bh.initialize();

/***
 * Map out _clients_bh to our input with the typeahead plugin
 */
$('#input-client').typeahead(null, {
	name: 'clients',
	displayKey: 'name',
	source: _clients_bh.ttAdapter()
});


{% if clients and overview %}
{% include "js/home.js" %}
{% endif %}

{% if clients and report %}
{% include "js/clients-report.js" %}
{% endif %}

{% if client and overview %}
{% include "js/client.js" %}
{% endif %}

{% if backup and report and client %}
{% include "js/backup-report.js" %}
{% endif %}

{% if not backup and report and client %}
{% include "js/client-report.js" %}
{% endif %}

{% if live %}
{% include "js/live-report.js" %}
{% endif %}

var _async_ajax = function(b) {
	$.ajaxSetup({
		async: b
	});
}

$(function() {
	_async_ajax(false);

	/***
	 * Action on the 'refresh' button
	 */
	$('#refresh').on('click', function(e) {
		e.preventDefault();
		{% if clients %}
		_clients();
		{% endif %}
		{% if client %}
		_client();
		{% endif %}
		{% if live %}
		_live();
		{% endif %}
		{% if not login %}
		_check_running();
		{% endif %}
	});

	/***
	 * trigger action on the 'search field' when the 'enter' key is pressed
	 */
	var search = $('input[id="input-client"]');
	search.keypress(function(e) {
		if (e.which == 13) {
			window.location = '{{ url_for("client") }}?name='+search.val();
		}
	});

	/***
	 * add a listener to the '.clickable' element dynamically added in the document (see _client and _clients function)
	 */
	$( document ).on('click', '.clickable', function() {
		window.location = $(this).find('a').attr('href');
	});

	/***
	 * initialize our page if needed
	 */
	{% if not login %}
	_check_running();
	{% endif %}
	{% if clients %}
	_clients();
	{% endif %}
	{% if client %}
	_client();
	{% endif %}
	{% if live %}
	_live();
	{% endif %}

	{% if not report %}
	/***
	 * auto-refresh our page if needed
	 */
	var auto_refresh = setInterval(function() {
		{% if clients %}
		_clients();
		{% endif %}
		{% if client %}
		_client();
		{% endif %}
		{% if live %}
		_live();
		{% endif %}
		return;
	}, {{ config.REFRESH * 1000 }});
	{% endif %}

	{% if not login %}
	var refresh_running = setInterval(function () {
		_check_running();
	}, {{ config.REFRESH * 1000 }});
	{% endif %}

	{% if tree %}
	{% include "js/client-browse.js" %}
	{% endif %}
});
