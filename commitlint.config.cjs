module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    // 允许中文 subject，不限制大小写
    'subject-case': [0],
    'subject-full-stop': [2, 'never', '.'],
    'header-max-length': [2, 'always', 100],
    'body-max-line-length': [0, 'always'],
    'footer-max-line-length': [0, 'always']
  }
}
