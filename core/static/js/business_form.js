document.addEventListener('DOMContentLoaded', function () {

    const documentInput = document.getElementById('id_document');
    const btnCnpj = document.getElementById('btn-search-cnpj');
    const btnCep = document.getElementById('btn-search-cep');
    const cepInput = document.getElementById('id_zip_code');
    const phoneInput = document.getElementById('id_phone');

    /* MÁSCARA CNPJ */
    if (documentInput) {
        documentInput.addEventListener('input', function () {
            let value = documentInput.value.replace(/\D/g, '').slice(0, 14);

            value = value
                .replace(/^(\d{2})(\d)/, '$1.$2')
                .replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
                .replace(/^(\d{2})\.(\d{3})\.(\d{3})(\d)/, '$1.$2.$3/$4')
                .replace(/^(\d{2})\.(\d{3})\.(\d{3})\/(\d{4})(\d)/, '$1.$2.$3/$4-$5');

            documentInput.value = value;
        });
    }

    /* BUSCA CNPJ */
    if (btnCnpj) {
        btnCnpj.addEventListener('click', function () {

            const cnpj = documentInput.value.replace(/\D/g, '');

            if (cnpj.length !== 14) {
                alert('CNPJ inválido');
                return;
            }

            fetch(`https://brasilapi.com.br/api/cnpj/v1/${cnpj}`)
                .then(r => r.json())
                .then(data => {
                    document.getElementById('id_name').value = data.razao_social || '';
                    document.getElementById('id_fantasy_name').value = data.nome_fantasia || '';
                    document.getElementById('id_zip_code').value = data.cep || '';
                    document.getElementById('id_street').value = data.logradouro || '';
                    document.getElementById('id_district').value = data.bairro || '';
                    document.getElementById('id_city').value = data.municipio || '';
                    document.getElementById('id_state').value = data.uf || '';
                })
                .catch(() => alert('Erro ao buscar CNPJ'));
        });
    }

    /* BUSCA CEP */
    if (btnCep) {
        btnCep.addEventListener('click', function () {

            const cep = cepInput.value.replace(/\D/g, '');

            if (cep.length !== 8) {
                alert('CEP inválido');
                return;
            }

            fetch(`https://viacep.com.br/ws/${cep}/json/`)
                .then(r => r.json())
                .then(data => {
                    document.getElementById('id_street').value = data.logradouro || '';
                    document.getElementById('id_district').value = data.bairro || '';
                    document.getElementById('id_city').value = data.localidade || '';
                    document.getElementById('id_state').value = data.uf || '';
                    document.getElementById('id_city_code').value = data.ibge || '';
                })
                .catch(() => alert('Erro ao buscar CEP'));
        });
    }

});