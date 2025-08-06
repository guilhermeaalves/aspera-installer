import os
import paramiko
import socket
import random
import time
import threading
import customtkinter as ctk
from PIL import Image
import gdown

LICENSES_DIR = os.path.join(os.path.dirname(__file__), "licenses_aspera")

INSTALLER_IDS = {
    "debian": ("1wKzrIEbiCszxbAcEmtI6ytRdd3i1rQD_", "aspera.deb"),
    "rhel": ("19ZmNTIpbJXPoUH308o68ytEK8i8xSF69", "aspera.rpm"),
    "aix": ("1klcsw2G1TRBEPxqRUsvPgVCIXV1hqTP_", "aspera.sh"),
    "linux_genérico": ("", "")
}

class AsperaInstallerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Aspera HSTS Installer")
        self.set_window_position()
        self.geometry("760x650")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # Logo
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "aspera_logo.png")
            image = ctk.CTkImage(light_image=Image.open(logo_path), size=(200, 60))
            logo = ctk.CTkLabel(self, image=image, text="")
            logo.pack(pady=(15, 5))
        except Exception:
            logo = ctk.CTkLabel(self, text="Aspera HSTS Installer", font=ctk.CTkFont(size=22, weight="bold"))
            logo.pack(pady=(15, 5))

        main_frame = ctk.CTkFrame(self)
        main_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.entry_host = self.create_labeled_entry(main_frame, "IP ou hostname da VM:")
        self.entry_user = self.create_labeled_entry(main_frame, "Usuário SSH:")
        self.entry_pass = self.create_labeled_entry(main_frame, "Senha SSH:", show="*")
        self.entry_key = self.create_labeled_entry(main_frame, "Caminho para chave SSH:")

        self.btn_start = ctk.CTkButton(main_frame, text="🚀 Iniciar Instalação", command=self.run_installation_thread)
        self.btn_start.pack(pady=15)

        self.progress = ctk.CTkProgressBar(main_frame, width=600)
        self.progress.pack(pady=(5, 15))
        self.progress.set(0)

        self.text_output = ctk.CTkTextbox(main_frame, width=700, height=250, wrap="word")
        self.text_output.pack(padx=10, pady=(0, 15))
        self.text_output.configure(state="disabled")

    def set_window_position(self):
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = 760
        height = 650
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def create_labeled_entry(self, parent, label_text, show=None):
        label = ctk.CTkLabel(parent, text=label_text)
        label.pack(pady=(8, 0))
        entry = ctk.CTkEntry(parent, width=400, show=show)
        entry.pack()
        return entry

    def log(self, message):
        self.text_output.configure(state="normal")
        self.text_output.insert("end", message + "\n")
        self.text_output.see("end")
        self.text_output.configure(state="disabled")

    def update_progress(self, value):
        self.progress.set(value)
        self.update_idletasks()

    def run_installation_thread(self):
        thread = threading.Thread(target=self.main_process)
        thread.start()

    def conectar_ssh(self, host, user="root", password=None, key_path=None):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if key_path:
                ssh.connect(host, username=user, key_filename=key_path)
            else:
                ssh.connect(host, username=user, password=password)
            self.log(f"✅ Conectado a {host}")
            return ssh
        except (socket.error, paramiko.AuthenticationException) as e:
            self.log(f"❌ Erro de conexão com {host}: {e}")
            return None

    def detect_os(self, ssh):
        try:
            stdin, stdout, stderr = ssh.exec_command("cat /etc/os-release")
            os_info = stdout.read().decode().lower()
            if "debian" in os_info or "ubuntu" in os_info:
                return "debian"
            elif "rhel" in os_info or "centos" in os_info:
                return "rhel"
            else:
                return "linux_genérico"
        except Exception as e:
            self.log(f"Erro ao detectar sistema operacional: {e}")
            return "linux_genérico"

    def buscar_licenca(self):
        try:
            lic_files = [f for f in os.listdir(LICENSES_DIR) if f.endswith(".aspera-license")]
            if not lic_files:
                self.log("❌ Nenhuma licença .aspera-license encontrada na pasta.")
                return None

            self.log("🎯 Selecionando licença aleatória...")
            for i in range(10):
                self.update_progress((i+1)/10)
                time.sleep(0.05)

            return os.path.join(LICENSES_DIR, random.choice(lic_files))
        except Exception as e:
            self.log(f"Erro ao buscar licença: {e}")
            return None

    def send_file(self, ssh, local_path, remote_path):
        try:
            sftp = ssh.open_sftp()
            file_size = os.path.getsize(local_path)
            self.log(f"📦 Enviando {os.path.basename(local_path)} ({file_size/1024:.2f} KB)...")
            def callback_transferred(bytes_transferred, total_bytes):
                progress = bytes_transferred / file_size
                self.update_progress(progress)

            sftp.put(local_path, remote_path, callback=callback_transferred)
            sftp.close()
            self.update_progress(1)
            self.log(f"✅ Arquivo enviado para {remote_path}")
            return True
        except Exception as e:
            self.log(f"❌ Erro ao enviar arquivo: {e}")
            return False

    def baixar_instalador(self, os_type):
        file_id, filename = INSTALLER_IDS.get(os_type, ("", ""))
        if not file_id:
            self.log(f"❌ Instalador não disponível para o tipo: {os_type}")
            return None

        output_path = os.path.join("/tmp", filename)
        url = f"https://drive.google.com/uc?id={file_id}"
        self.log(f"⬇️ Baixando instalador para {os_type}...")

        try:
            gdown.download(url, output_path, quiet=False)
            self.update_progress(1)
            return output_path
        except Exception as e:
            self.log(f"Erro ao baixar instalador: {e}")
            return None

    def install_package(self, ssh, os_type, remote_path):
        try:
            if os_type == "debian":
                cmd = f"sudo dpkg -i {remote_path}"
            elif os_type == "rhel":
                cmd = f"sudo rpm -ivh {remote_path}"
            elif os_type == "aix":
                cmd = f"sudo chmod +x {remote_path} && sudo sh {remote_path}"
            else:
                cmd = f"sudo tar -xzf {remote_path} -C /opt/ && echo 'Extraído em /opt/'"

            self.log(f"🛠️ Instalando pacote: {os.path.basename(remote_path)}")
            stdin, stdout, stderr = ssh.exec_command(cmd)

            for i in range(10):
                time.sleep(0.4)
                self.update_progress((i+1)/10)

            output = stdout.read().decode()
            error = stderr.read().decode()
            if output.strip():
                self.log(f"✅ Saída:\n{output}")
            if error.strip():
                self.log(f"⚠️ Erros:\n{error}")

        except Exception as e:
            self.log(f"❌ Erro na instalação: {e}")

    def garantir_diretorio_licenca(self, ssh):
        try:
            ssh.exec_command("sudo mkdir -p /opt/aspera/etc")
            self.log("📁 Diretório /opt/aspera/etc criado ou já existente.")
        except Exception as e:
            self.log(f"Erro ao criar diretório: {e}")

    def mover_licenca_para_diretorio_final(self, ssh, remote_license_path):
        try:
            cmd = f"sudo mv {remote_license_path} /opt/aspera/etc/aspera-license"
            ssh.exec_command(cmd)
            self.log("✅ Licença movida para /opt/aspera/etc/")
        except Exception as e:
            self.log(f"Erro ao mover licença: {e}")

    def aplicar_licenca(self, ssh, remote_path):
        try:
            # Tente usar o caminho absoluto do ascp
            stdin, stdout, stderr = ssh.exec_command("/opt/aspera/bin/ascp -A")
            self.log(stdout.read().decode())
            self.log(stderr.read().decode())
        except Exception as e:
            self.log(f"Erro ao aplicar licença: {e}")

    def main_process(self):
        self.btn_start.configure(state="disabled")
        self.progress.set(0)

        # Define as etapas principais do processo
        steps = [
            "conectar_ssh",
            "detect_os",
            "baixar_instalador",
            "send_file_installer",
            "install_package",
            "buscar_licenca",
            "send_file_licenca",
            "garantir_diretorio_licenca",
            "mover_licenca_para_diretorio_final",
            "aplicar_licenca"
        ]
        total_steps = len(steps)
        current_step = 0

        def step_progress():
            # Garante que a barra nunca fique cheia antes do fim
            self.update_progress(min(current_step / total_steps, 0.99))

        host = self.entry_host.get().strip()
        user = self.entry_user.get().strip()
        password = self.entry_pass.get().strip() or None
        key_path = self.entry_key.get().strip() or None
        if key_path:
            key_path = os.path.expanduser(key_path)

        # 1. Conectar SSH
        ssh = self.conectar_ssh(host, user, password, key_path)
        current_step += 1
        step_progress()
        if not ssh:
            self.btn_start.configure(state="normal")
            return

        # 2. Detectar SO
        os_type = self.detect_os(ssh)
        self.log(f"🔍 SO detectado: {os_type}")
        current_step += 1
        step_progress()

        # 3. Baixar instalador
        local_installer = self.baixar_instalador(os_type)
        current_step += 1
        step_progress()
        if not local_installer or not os.path.isfile(local_installer):
            self.log(f"❌ Falha ao baixar instalador para {os_type}")
            self.btn_start.configure(state="normal")
            return

        # 4. Enviar instalador
        remote_installer_path = f"/tmp/{os.path.basename(local_installer)}"
        if not self.send_file(ssh, local_installer, remote_installer_path):
            self.btn_start.configure(state="normal")
            return
        current_step += 1
        step_progress()

        # 5. Instalar pacote
        self.install_package(ssh, os_type, remote_installer_path)
        current_step += 1
        step_progress()

        # 6. Buscar licença
        lic_path = self.buscar_licenca()
        current_step += 1
        step_progress()
        if not lic_path:
            self.btn_start.configure(state="normal")
            return

        # 7. Enviar licença
        remote_lic_path = f"/tmp/{os.path.basename(lic_path)}"
        if not self.send_file(ssh, lic_path, remote_lic_path):
            self.btn_start.configure(state="normal")
            return
        current_step += 1
        step_progress()

        # 8. Garantir diretório licença
        self.garantir_diretorio_licenca(ssh)
        current_step += 1
        step_progress()

        # 9. Mover licença
        self.mover_licenca_para_diretorio_final(ssh, remote_lic_path)
        current_step += 1
        step_progress()

        # 10. Aplicar licença
        self.aplicar_licenca(ssh, remote_lic_path)
        current_step += 1
        step_progress()

        ssh.close()
        self.log("🎉 Instalação e licenciamento concluídos!")
        self.progress.set(1)  # Barra cheia ao final
        self.btn_start.configure(state="normal")

if __name__ == "__main__":
    app = AsperaInstallerApp()
    app.mainloop()