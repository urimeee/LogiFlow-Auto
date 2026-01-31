module.exports = {
  apps: [
    {
      name: 'logistics-app',
      script: 'python',
      args: '-m streamlit run app.py --server.port 3000 --server.address 0.0.0.0 --server.headless true',
      cwd: '/home/user/webapp',
      env: {
        STREAMLIT_SERVER_PORT: 3000,
        STREAMLIT_SERVER_ADDRESS: '0.0.0.0',
        STREAMLIT_SERVER_HEADLESS: 'true'
      },
      watch: false,
      instances: 1,
      exec_mode: 'fork',
      interpreter: 'none'
    }
  ]
}
