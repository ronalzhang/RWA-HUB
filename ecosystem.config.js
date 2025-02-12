module.exports = {
  apps: [{
    name: "rwa-hub",
    script: "run.py",
    interpreter: "/usr/bin/python3",
    env: {
      DATABASE_URL: "postgresql://rwa_hub_user:3YIeu6i1Nuyb6z8wRAxdctbMJVrSseJB@dpg-cu6b270gph6c73c50eag-a.oregon-postgres.render.com/rwa_hub",
      FLASK_ENV: "production",
      SECRET_KEY: "your-secret-key-here",
      QINIU_ACCESS_KEY: "SGMhwmXf7wRlmsgXU4xfqzDH_DxczWhhoDEjyYE9",
      QINIU_SECRET_KEY: "6JynlQeJEDWt4VIjZV8sDdSAFZMrZ3GFE0fIz07-",
      QINIU_BUCKET_NAME: "rwa-hub",
      QINIU_DOMAIN: "sqbw3uvy8.sabkt.gdipper.com",
      PORT: "10000",
      WAITRESS_THREADS: "8"
    },
    exec_mode: "fork",
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: "1G",
    env_production: {
      NODE_ENV: "production"
    }
  }]
}
