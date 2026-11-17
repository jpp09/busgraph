
var functionConsultaLinha = null;

var consultaLinha = function(qry, callback) {
	$('#linha_numero').addClass("loading");
	try {
		$.post({
			url: 'consulta_linha.php',
			data: { 'term': qry }
		}).done(function(data) {
			$('#linha_numero').removeClass("loading");
			callback(data);
		}).always(function() {
			$('#linha_numero').removeClass("loading");
		});
	} catch (e) {
		$('#linha_numero').removeClass("loading");
	}
}

$(document).ready(function() {
	if ($('#linha_numero')) {
		$("#linha_numero").on("click", function() {
			$(this).select();
		});
		$('#linha_numero').data('noresults-text', "Nenhuma linha localizada");
		$('#linha_numero').autoComplete({
			minLength: 1,
			resolver: 'custom',
			events: {
				search: function(qry, callback) {
					if (functionConsultaLinha != null) {
						clearTimeout(functionConsultaLinha);
					}
					functionConsultaLinha = setTimeout(consultaLinha, 400, qry, callback);
				}
			}
		});
		$('#linha_numero').on('autocomplete.select', function(evt, item) {
			if ((item !== undefined) && (item.text !== undefined))
				setDadosConsultaLinha(JSON.parse(item.text));
		});
	}
});
var setDadosConsultaLinha = function(data) {
	$('#detalhe_linha').html("&nbsp;");
	$('#detalhe_linha').addClass("loading");
	$('#linha_numero').autoComplete('set', { value: data.numero_linha, text: data.numero_linha + ' - ' + data.nome });
	$.post({
		url: 'detalhe_linha.php',
		data: { 'term': data.linhaosletra }
	}).done(function(data) {
		$('#detalhe_linha').removeClass("loading");
		$('#detalhe_linha').html(data);
	}).always(function() {
		$('#detalhe_linha').removeClass("loading");
	});
}