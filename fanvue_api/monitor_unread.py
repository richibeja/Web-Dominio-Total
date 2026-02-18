"""
Script para monitorear chats no leídos y notificaciones en Fanvue
Útil para verificar el estado de mensajes pendientes
"""
import os
import sys
import io

# Fix para Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Agregar el directorio raíz del proyecto al path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
from fanvue_api.fanvue_client import FanvueAPI

load_dotenv()

def main():
    """Muestra el conteo de chats no leídos y notificaciones"""
    print("=" * 60)
    print("📊 MONITOR DE CHATS NO LEÍDOS - FANVUE")
    print("=" * 60)
    print()
    
    api = FanvueAPI()
    
    # Verificar si hay token
    token = api.get_access_token()
    if not token:
        print("❌ Error: No se encontró FANVUE_ACCESS_TOKEN en .env")
        print("   Necesitas obtener el token mediante OAuth primero.")
        print()
        print("   Ejecuta: python obtener_token_rapido.py")
        return
    
    print("🔄 Consultando conteo de no leídos...")
    print()
    
    unread_data = api.get_unread_counts()
    
    if not unread_data:
        print("❌ No se pudo obtener la información")
        print("   Verifica que el Access Token sea válido")
        return
    
    # Mostrar información
    print("📨 CHATS NO LEÍDOS:")
    print(f"   Conversaciones: {unread_data.get('unreadChatsCount', 0)}")
    print(f"   Mensajes totales: {unread_data.get('unreadMessagesCount', 0)}")
    print()
    
    notifications = unread_data.get('unreadNotifications', {})
    if notifications:
        print("🔔 NOTIFICACIONES:")
        notification_labels = {
            'newFollower': 'Nuevos seguidores',
            'newPostComment': 'Comentarios en posts',
            'newPostLike': 'Likes en posts',
            'newPurchase': 'Nuevas compras',
            'newSubscriber': 'Nuevos suscriptores',
            'newTip': 'Nuevas propinas',
            'newPromotion': 'Nuevas promociones'
        }
        
        total_notifications = 0
        for key, label in notification_labels.items():
            count = notifications.get(key, 0)
            if count > 0:
                print(f"   {label}: {count}")
                total_notifications += count
        
        if total_notifications == 0:
            print("   ✅ No hay notificaciones pendientes")
        else:
            print(f"\n   Total de notificaciones: {total_notifications}")
    else:
        print("🔔 NOTIFICACIONES:")
        print("   ✅ No hay notificaciones pendientes")
    
    print()
    print("=" * 60)
    
    # Sugerir acción si hay mensajes no leídos
    if unread_data.get('unreadMessagesCount', 0) > 0:
        print()
        print("💡 SUGERENCIA:")
        print("   Hay mensajes pendientes. El bot debería responder automáticamente")
        print("   cuando reciba webhooks de Fanvue.")
        print()
        print("   Verifica que el webhook handler esté corriendo:")
        print("   python fanvue_api/webhook_handler.py")

if __name__ == "__main__":
    main()
