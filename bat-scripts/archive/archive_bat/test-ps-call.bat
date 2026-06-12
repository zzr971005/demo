# 测试 PowerShell 调用批处理文件
Write-Host '测试开始...'

# 使用 & operator 调用批处理文件
& 'd:\\期货自动进化因子挖掘系统\\bat启动文件夹\\test-pause.bat'

Write-Host '批处理文件已结束，这行应该显示'
