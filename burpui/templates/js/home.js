
/***
 * Here is the 'clients' part
 * It is available on the global clients view
 */

/***
 * First we map some burp status with some style
 */
var __status = {
	'client crashed': 'danger',
	'server crashed': 'danger',
	'running': 'info',
};

/***
 * _clients: function that retrieve up-to-date informations from the burp server
 * JSON format:
 * {
 *   "results": [
 *     {
 *       "last": "2014-05-12 19:40:02",
 *       "name": "client1",
 *       "state": "idle"
 *     },
 *     {
 *       "last": "never",
 *       "name": "client2",
 *       "state": "idle"
 *     }
 *   ]
 * }
 *  The JSON is then parsed into a table
 */
var _clients = function() {
	url = '{{ url_for("clients") }}';
	$.getJSON(url, function(data) {
		$('#table-clients > tbody:last').empty();
		if (!data.resuts && data.errors) {
			alert(data.errors[0]);
			return;
		}
		if (!data.results) {
			return;
		}
		$.each(data.results, function(j, c) {
			clas = '';
			if (__status[c.state] != undefined) {
				clas = ' '+__status[c.state];
			}
			$('#table-clients > tbody:last').append('<tr class="clickable'+clas+'" style="cursor: pointer;"><td><a href="{{ url_for("client") }}?name='+c.name+'" style="color: inherit; text-decoration: inherit;">'+c.name+'</a></td><td>'+c.state+'</td><td>'+c.last+'</td></tr>');
		});
	});
};