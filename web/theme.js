(() => {
  const chave = 'vulcantech-tema';
  const html = document.documentElement;
  const botoes = document.querySelectorAll('.theme-toggle');

  function aplicarTema(tema) {
    html.dataset.theme = tema;
    localStorage.setItem(chave, tema);
    botoes.forEach((botao) => {
      const escuro = tema === 'dark';
      botao.innerHTML = escuro ? '☀ <span>Tema</span>' : '☾ <span>Tema</span>';
      botao.setAttribute('aria-label', escuro ? 'Ativar tema claro' : 'Ativar tema escuro');
      botao.title = escuro ? 'Mudar para tema claro' : 'Mudar para tema escuro';
    });
  }

  aplicarTema(localStorage.getItem(chave) || 'light');
  botoes.forEach((botao) => {
    botao.addEventListener('click', () => {
      aplicarTema(html.dataset.theme === 'dark' ? 'light' : 'dark');
    });
  });

  const cabecalho = document.querySelector('.home-header, .site-header');
  if (cabecalho) {
    const indicadorApi = document.createElement('span');
    indicadorApi.className = 'api-status api-pending';
    indicadorApi.setAttribute('role', 'status');
    indicadorApi.setAttribute('aria-live', 'polite');
    indicadorApi.innerHTML = '<i></i><span>Verificando API</span>';
    const botaoTema = cabecalho.querySelector('.theme-toggle');
    cabecalho.insertBefore(indicadorApi, botaoTema || null);

    async function verificarApi() {
      try {
        const resposta = await window.vulcanFetch('/health', { cache: 'no-store' });
        if (!resposta.ok) throw new Error('API indisponível');
        const dados = await resposta.json();
        if (dados.status !== 'ok') throw new Error('API indisponível');
        indicadorApi.className = 'api-status api-online';
        indicadorApi.setAttribute('aria-label', 'API ativa');
        indicadorApi.title = 'API ativa';
        indicadorApi.innerHTML = '<i></i><span>API ativa</span>';
      } catch (_) {
        indicadorApi.className = 'api-status api-offline';
        indicadorApi.setAttribute('aria-label', 'API indisponível');
        indicadorApi.title = 'API indisponível';
        indicadorApi.innerHTML = '<i></i><span>API indisponível</span>';
      }
    }

    verificarApi();
    window.setInterval(verificarApi, 10000);
  }
})();
