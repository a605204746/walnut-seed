package com.walnut.seed.module.system.controller.system;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.io.FileUtil;
import cn.hutool.core.util.ObjectUtil;
import cn.hutool.crypto.digest.BCrypt;
import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.domain.ApiResponse;
import com.walnut.seed.common.core.utils.StringUtils;
import com.walnut.seed.common.core.utils.file.MimeTypeUtils;
import com.walnut.seed.common.encrypt.annotation.ApiEncrypt;
import com.walnut.seed.common.redis.idempotent.annotation.RepeatSubmit;
import com.walnut.seed.common.log.annotation.Log;
import com.walnut.seed.common.log.enums.BusinessType;
import com.walnut.seed.common.mybatis.helper.DataPermissionHelper;
import com.walnut.seed.common.satoken.utils.LoginHelper;
import com.walnut.seed.module.system.domain.req.SysUserReq;
import com.walnut.seed.module.system.domain.req.SysUserPasswordReq;
import com.walnut.seed.module.system.domain.req.SysUserProfileReq;
import com.walnut.seed.module.system.domain.resp.ProfileUserResp;
import com.walnut.seed.module.system.domain.resp.SysUserResp;
import com.walnut.seed.common.oss.FileStorageService;
import com.walnut.seed.common.oss.model.UploadResult;
import com.walnut.seed.module.system.service.SysUserService;
import org.springframework.http.MediaType;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.Arrays;

/**
 * 个人信息 业务处理
 *
 * @author deepin_sir
 */
@Validated
@RequiredArgsConstructor
@RestController
@RequestMapping("/system/user/profile")
public class SysProfileController {

    private final SysUserService userService;
    private final FileStorageService fileStorageService;

    /**
     * 个人信息
     */
    @GetMapping
    public ApiResponse<ProfileVo> profile() {
        SysUserResp user = userService.selectUserById(LoginHelper.getUserId());
        String roleGroup = userService.selectUserRoleGroup(user.getId());
        String postGroup = userService.selectUserPostGroup(user.getId());
        // 单独做一个vo专门给个人中心用 避免数据被脱敏
        ProfileUserResp profileUser = BeanUtil.toBean(user, ProfileUserResp.class);
        ProfileVo profileVo = new ProfileVo(profileUser, roleGroup, postGroup);
        return ApiResponse.ok(profileVo);
    }

    /**
     * 修改用户信息
     */
    @RepeatSubmit
    @Log(title = "个人信息", businessType = BusinessType.UPDATE)
    @PutMapping
    public ApiResponse<Void> updateProfile(@Validated @RequestBody SysUserProfileReq profile) {
        SysUserReq req = BeanUtil.toBean(profile, SysUserReq.class);
        req.setId(LoginHelper.getUserId());
        String username = LoginHelper.getUsername();
        if (StringUtils.isNotEmpty(req.getPhonenumber()) && !userService.checkPhoneUnique(req)) {
            return ApiResponse.fail("修改用户'" + username + "'失败，手机号码已存在");
        }
        if (StringUtils.isNotEmpty(req.getEmail()) && !userService.checkEmailUnique(req)) {
            return ApiResponse.fail("修改用户'" + username + "'失败，邮箱账号已存在");
        }
        int rows = DataPermissionHelper.ignore(() -> userService.updateUserProfile(req));
        if (rows > 0) {
            return ApiResponse.ok();
        }
        return ApiResponse.fail("修改个人信息异常，请联系管理员");
    }

    /**
     * 重置密码
     *
     * @param req 新旧密码
     */
    @RepeatSubmit
    @ApiEncrypt
    @Log(title = "个人信息", businessType = BusinessType.UPDATE)
    @PutMapping("/updatePwd")
    public ApiResponse<Void> updatePwd(@Validated @RequestBody SysUserPasswordReq req) {
        SysUserResp user = userService.selectUserById(LoginHelper.getUserId());
        String password = user.getPassword();
        if (!BCrypt.checkpw(req.getOldPassword(), password)) {
            return ApiResponse.fail("修改密码失败，旧密码错误");
        }
        if (BCrypt.checkpw(req.getNewPassword(), password)) {
            return ApiResponse.fail("新密码不能与旧密码相同");
        }
        int rows = DataPermissionHelper.ignore(() -> userService.resetUserPwd(user.getId(), BCrypt.hashpw(req.getNewPassword())));
        if (rows > 0) {
            return ApiResponse.ok();
        }
        return ApiResponse.fail("修改密码异常，请联系管理员");
    }

    /**
     * 头像上传
     *
     * @param avatarfile 用户头像
     */
    @RepeatSubmit
    @Log(title = "用户头像", businessType = BusinessType.UPDATE)
    @PostMapping(value = "/avatar", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ApiResponse<AvatarVo> avatar(@RequestPart("avatarfile") MultipartFile avatarfile) {
        if (ObjectUtil.isNotNull(avatarfile) && !avatarfile.isEmpty()) {
            String extension = FileUtil.extName(avatarfile.getOriginalFilename());
            if (!StringUtils.equalsAnyIgnoreCase(extension, MimeTypeUtils.IMAGE_EXTENSION)) {
                return ApiResponse.fail("文件格式不正确，请上传" + Arrays.toString(MimeTypeUtils.IMAGE_EXTENSION) + "格式");
            }
            UploadResult result = fileStorageService.upload(avatarfile);
            boolean updateSuccess = DataPermissionHelper.ignore(() ->
                userService.updateUserAvatar(LoginHelper.getUserId(), result.getUrl()));
            if (updateSuccess) {
                return ApiResponse.ok(new AvatarVo(result.getUrl()));
            }
        }
        return ApiResponse.fail("上传图片异常，请联系管理员");
    }

    /**
     * 用户头像信息
     *
     * @param imgUrl 头像地址
     */
    public record AvatarVo(String imgUrl) {}

    /**
     * 用户个人信息
     *
     * @param user      用户信息
     * @param roleGroup 用户所属角色组
     * @param postGroup 用户所属岗位组
     */
    public record ProfileVo(ProfileUserResp user, String roleGroup, String postGroup) {}

}
