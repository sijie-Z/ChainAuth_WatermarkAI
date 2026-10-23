"""
任务调度
"""
scheduler = None


def init_scheduler(app):
    """初始化任务调度器（APScheduler 为可选依赖，导入放在函数内）"""
    global scheduler
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = BackgroundScheduler()
    from app.utils.backup import backup_database

    @scheduler.scheduled_job(CronTrigger(hour=2, minute=0))
    def daily_backup():
        """每日凌晨2点备份"""
        with app.app_context():
            try:
                backup_file = backup_database()
                app.logger.info(f'数据库备份成功: {backup_file}')
            except Exception as e:
                app.logger.error(f'数据库备份失败: {e}')

    @scheduler.scheduled_job(CronTrigger(hour=3, minute=0))
    def cleanup_temp_files():
        """每日凌晨3点清理临时文件"""
        import os
        import shutil
        from datetime import datetime, timedelta

        with app.app_context():
            temp_dirs = [
                app.config.get('UPLOAD_FOLDER', './uploads'),
                app.config.get('EXTRACTED_FOLDER', './extracted')
            ]

            cutoff = datetime.now() - timedelta(days=7)

            for temp_dir in temp_dirs:
                if not os.path.exists(temp_dir):
                    continue

                for f in os.listdir(temp_dir):
                    path = os.path.join(temp_dir, f)
                    if os.path.isfile(path):
                        stat = os.stat(path)
                        mtime = datetime.fromtimestamp(stat.st_mtime)
                        if mtime < cutoff:
                            os.remove(path)
                            app.logger.info(f'已删除临时文件: {path}')

    @scheduler.scheduled_job(CronTrigger(hour=4, minute=0))
    def check_expired_licenses():
        """每日凌晨4点检查过期授权"""
        with app.app_context():
            from app.extensions import db
            from app.models.license import License
            from datetime import datetime

            expired = License.query.filter(
                License.status == 'active',
                License.end_time < datetime.utcnow()
            ).all()

            for license in expired:
                license.status = 'expired'

            db.session.commit()
            app.logger.info(f'已更新{len(expired)}个过期授权')

    @scheduler.scheduled_job(CronTrigger(hour=5, minute=0))
    def purge_expired_tokens():
        """每日凌晨5点清理过期的撤销 Token 记录"""
        with app.app_context():
            from datetime import datetime
            from app.extensions import db
            from app.models.user import UserToken

            deleted = UserToken.query.filter(
                UserToken.expires_at < datetime.utcnow()
            ).delete(synchronize_session=False)
            db.session.commit()
            app.logger.info(f'已清理{deleted}条过期 Token 记录')

    @scheduler.scheduled_job('interval', minutes=5)
    def reconcile_async_tasks():
        """每 5 分钟回收超时的异步任务"""
        with app.app_context():
            try:
                from app.services.task_service import reconcile_stuck
                result = reconcile_stuck()
                if result['requeued'] or result['failed']:
                    app.logger.warning(
                        f"异步任务对账: 重新排队 {result['requeued']}, "
                        f"失败 {result['failed']}"
                    )
            except Exception as exc:
                app.logger.error(f'异步任务对账失败: {exc}')

    @scheduler.scheduled_job('interval', minutes=1)
    def dispatch_email_notifications():
        """每分钟派发到期的邮件通知"""
        with app.app_context():
            try:
                from app.services.email_service import dispatch_pending_emails
                result = dispatch_pending_emails()
                if result.get('sent') or result.get('failed'):
                    app.logger.info(
                        f"邮件通知: 发送 {result.get('sent', 0)}, "
                        f"失败 {result.get('failed', 0)}"
                    )
            except Exception as exc:
                app.logger.error(f'邮件通知派发失败: {exc}')

    @scheduler.scheduled_job('interval', minutes=1)
    def dispatch_webhook_notifications():
        """每分钟派发到期的 Webhook 通知"""
        with app.app_context():
            try:
                from app.services.webhook_service import dispatch_pending_webhooks
                result = dispatch_pending_webhooks()
                if result.get('sent') or result.get('failed'):
                    app.logger.info(
                        f"Webhook 通知: 发送 {result.get('sent', 0)}, "
                        f"失败 {result.get('failed', 0)}"
                    )
            except Exception as exc:
                app.logger.error(f'Webhook 通知派发失败: {exc}')

    scheduler.start()
    app.logger.info('任务调度器已启动')


def shutdown_scheduler():
    """关闭调度器"""
    if scheduler is not None:
        scheduler.shutdown()