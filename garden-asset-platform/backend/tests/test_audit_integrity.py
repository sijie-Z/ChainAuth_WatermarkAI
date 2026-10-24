"""审计日志完整性签名测试"""
from app.extensions import db
from app.models import OperationLog
from app.services.audit_integrity_service import (
    rebuild_audit_signatures,
    verify_audit_logs,
)


def _write_logs(app):
    with app.app_context():
        OperationLog.log(
            user=None,
            action='test_audit_a',
            module='asset',
            description='第一条测试审计日志',
        )
        OperationLog.log(
            user=None,
            action='test_audit_b',
            module='license',
            description='第二条测试审计日志',
            extra_data={'note': 'extra'},
        )


def test_new_logs_are_signed_and_valid(app):
    _write_logs(app)

    with app.app_context():
        result = verify_audit_logs()

    assert result['total'] >= 2
    assert result['signed'] >= 2
    assert result['unsigned'] == 0
    assert result['invalid'] == 0
    assert result['status'] == 'ok'


def test_tampered_log_is_detected(app):
    _write_logs(app)

    with app.app_context():
        log = OperationLog.query.filter_by(action='test_audit_a').first()
        log.description = '被篡改的描述'
        db.session.commit()
        result = verify_audit_logs()

    assert result['invalid'] == 1
    assert result['status'] == 'invalid'
    assert result['samples'][0]['action'] == 'test_audit_a'


def test_unsigned_logs_are_reported_and_can_be_rebuilt(app):
    _write_logs(app)

    with app.app_context():
        log = OperationLog.query.filter_by(action='test_audit_a').first()
        log.integrity_hash = None
        db.session.commit()
        before = verify_audit_logs()
        assert before['unsigned'] == 1
        assert before['status'] == 'unsigned'

        rebuilt = rebuild_audit_signatures()
        after = verify_audit_logs()

    assert rebuilt['updated'] >= 2
    assert after['unsigned'] == 0
    assert after['invalid'] == 0
    assert after['status'] == 'ok'


def test_integrity_endpoint_is_admin_only(client, auth_header, admin_header):
    response = client.get('/api/logs/integrity', headers=auth_header)
    assert response.status_code == 403

    response = client.get('/api/logs/integrity', headers=admin_header)
    assert response.status_code == 200
    payload = response.get_json()['data']
    assert payload['status'] in ('ok', 'unsigned', 'invalid')
    assert 'total' in payload
    assert 'signed' in payload


def test_audit_cli_verify(runner):
    result = runner.invoke(args=['audit', 'verify'])

    assert result.exit_code == 0
    assert '日志总数' in result.output
    assert '状态' in result.output
