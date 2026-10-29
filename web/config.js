(() => {
  const parametros = new URLSearchParams(window.location.search);
  const apiConfigurada = parametros.get('api');
  const porta = window.location.port;
  const frontendSeparado = porta === '5500' || porta === '8501';
  const apiPadrao = frontendSeparado
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : window.location.origin;

  window.VULCANTECH_API_BASE = (apiConfigurada || apiPadrao).replace(/\/$/, '');
  window.vulcanFetch = async (caminho, opcoes = {}) => {
    const resposta = await fetch(`${window.VULCANTECH_API_BASE}${caminho}`, {
      ...opcoes,
      credentials: 'include'
    });
    if (resposta.status === 401) {
      localStorage.removeItem('vulcantech-demo-access');
      if (window.location.pathname !== '/login') window.location.replace('/login');
    }
    return resposta;
  };
})();
