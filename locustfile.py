from locust import HttpUser, between, task


class SoporteUser(HttpUser):
    # Tiempo de espera entre acciones (1 a 5 segundos)
    wait_time = between(1, 5)
    token = None

    def on_start(self):
        """Se ejecuta al iniciar cada usuario simulado"""
        response = self.client.post(
            "/api/auth/login",
            json={"email": "admin@gmail.com", "password": "secret123"},
        )

        if response.status_code == 200:
            data = response.json()
            # CORRECCIÓN AQUÍ: Buscamos dentro de 'tokens'
            # Usamos .get() para evitar errores si la estructura cambia
            tokens = data.get("tokens", {})
            self.token = tokens.get("access_token")

            if self.token:
                print(f"✅ Login OK! Token capturado: {self.token[:10]}...")
            else:
                print(
                    f"⚠️ Login 200 pero NO encontré el token. Estructura recibida: {data.keys()}"
                )
        else:
            print(
                f"🔴 Falló Login: {response.status_code} - Respuesta: {response.text}"
            )

    @task(3)
    def ver_dashboard(self):
        if not self.token:
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.get("/api/tickets/dashboard/stats", headers=headers)

    @task(2)
    def listar_tickets(self):
        if not self.token:
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.get("/api/tickets/tickets", headers=headers)

    @task(1)
    def ver_categorias(self):
        if not self.token:
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.get("/api/tickets/categorias", headers=headers)
