package com.walnut.seed.module.system.listener;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.util.ObjectUtil;
import cn.hutool.crypto.digest.BCrypt;
import cn.hutool.http.HtmlUtil;
import cn.idev.excel.context.AnalysisContext;
import cn.idev.excel.event.AnalysisEventListener;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.ConstraintViolationException;
import lombok.extern.slf4j.Slf4j;
import com.walnut.seed.common.core.exception.ServiceException;
import com.walnut.seed.common.core.utils.SpringUtils;
import com.walnut.seed.common.core.utils.StreamUtils;
import com.walnut.seed.common.core.utils.ValidatorUtils;
import com.walnut.seed.common.excel.core.ExcelListener;
import com.walnut.seed.common.excel.core.ExcelResult;
import com.walnut.seed.module.system.domain.req.SysUserReq;
import com.walnut.seed.module.system.domain.resp.SysUserImportResp;
import com.walnut.seed.module.system.domain.resp.SysUserResp;
import com.walnut.seed.module.system.service.SysConfigService;
import com.walnut.seed.module.system.service.SysUserService;

import java.util.List;

/**
 * 系统用户自定义导入
 *
 * @author deepin_sir
 */
@Slf4j
public class SysUserImportListener extends AnalysisEventListener<SysUserImportResp> implements ExcelListener<SysUserImportResp> {

    private final SysUserService userService;

    private final String password;

    private final Boolean isUpdateSupport;

    private int successNum = 0;
    private int failureNum = 0;
    private final StringBuilder successMsg = new StringBuilder();
    private final StringBuilder failureMsg = new StringBuilder();

    public SysUserImportListener(Boolean isUpdateSupport) {
        String initPassword = SpringUtils.getBean(SysConfigService.class).selectConfigByKey("sys.user.initPassword");
        this.userService = SpringUtils.getBean(SysUserService.class);
        this.password = BCrypt.hashpw(initPassword);
        this.isUpdateSupport = isUpdateSupport;
    }

    @Override
    public void invoke(SysUserImportResp userVo, AnalysisContext context) {
        SysUserResp sysUser = this.userService.selectUserByUserName(userVo.getUserName());
        try {
            // 验证是否存在这个用户
            if (ObjectUtil.isNull(sysUser)) {
                SysUserReq user = BeanUtil.toBean(userVo, SysUserReq.class);
                ValidatorUtils.validate(user);
                user.setPassword(password);
                userService.insertUser(user);
                successNum++;
                successMsg.append("<br/>").append(successNum).append("、账号 ").append(user.getUserName()).append(" 导入成功");
            } else if (isUpdateSupport) {
                Long userId = sysUser.getId();
                SysUserReq user = BeanUtil.toBean(userVo, SysUserReq.class);
                user.setId(userId);
                ValidatorUtils.validate(user);
                userService.checkUserAllowed(user.getId());
                userService.checkUserDataScope(user.getId());
                userService.updateUser(user);
                successNum++;
                successMsg.append("<br/>").append(successNum).append("、账号 ").append(user.getUserName()).append(" 更新成功");
            } else {
                failureNum++;
                failureMsg.append("<br/>").append(failureNum).append("、账号 ").append(sysUser.getUserName()).append(" 已存在");
            }
        } catch (Exception e) {
            failureNum++;
            String msg = "<br/>" + failureNum + "、账号 " + HtmlUtil.cleanHtmlTag(userVo.getUserName()) + " 导入失败：";
            String message = e.getMessage();
            if (e instanceof ConstraintViolationException cvException) {
                message = StreamUtils.join(cvException.getConstraintViolations(), ConstraintViolation::getMessage, ", ");
            }
            failureMsg.append(msg).append(message);
            log.error(msg, e);
        }
    }

    @Override
    public void doAfterAllAnalysed(AnalysisContext context) {

    }

    @Override
    public ExcelResult<SysUserImportResp> getExcelResult() {
        return new ExcelResult<>() {

            @Override
            public String getAnalysis() {
                if (failureNum > 0) {
                    failureMsg.insert(0, "很抱歉，导入失败！共 " + failureNum + " 条数据格式不正确，错误如下：");
                    throw new ServiceException(failureMsg.toString());
                } else {
                    successMsg.insert(0, "恭喜您，数据已全部导入成功！共 " + successNum + " 条，数据如下：");
                }
                return successMsg.toString();
            }

            @Override
            public List<SysUserImportResp> getList() {
                return null;
            }

            @Override
            public List<String> getErrorList() {
                return null;
            }
        };
    }
}
