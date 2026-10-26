module.exports = {
  extends: ['@commitlint/config-conventional'],
  // Dependabot 的默认标题包含完整包路径和分组名，可能超过 100 字；
  // 仅豁免这类自动化提交，业务提交仍执行全部规范检查。
  ignores: [
    (message) => /^chore\((deps|docker)\):/.test(message)
  ],
  rules: {
    // 允许中文 subject，不限制大小写
    'subject-case': [0],
    'subject-full-stop': [2, 'never', '.'],
    'header-max-length': [2, 'always', 100],
    'body-max-line-length': [0, 'always'],
    'footer-max-line-length': [0, 'always']
  }
}
