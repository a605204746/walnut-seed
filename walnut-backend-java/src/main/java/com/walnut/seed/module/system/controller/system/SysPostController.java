package com.walnut.seed.module.system.controller.system;

import com.walnut.seed.common.core.domain.PageResult;

import cn.dev33.satoken.annotation.SaCheckPermission;
import cn.hutool.core.lang.tree.Tree;
import cn.hutool.core.util.ObjectUtil;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.constant.SystemConstants;
import com.walnut.seed.common.core.domain.ApiResponse;
import com.walnut.seed.common.excel.utils.ExcelUtil;
import com.walnut.seed.common.redis.idempotent.annotation.RepeatSubmit;
import com.walnut.seed.common.log.annotation.Log;
import com.walnut.seed.common.log.enums.BusinessType;
import com.walnut.seed.module.system.domain.req.SysDeptReq;
import com.walnut.seed.module.system.domain.req.SysPostReq;
import com.walnut.seed.module.system.domain.resp.SysPostResp;
import com.walnut.seed.module.system.service.SysDeptService;
import com.walnut.seed.module.system.service.SysPostService;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * 岗位信息操作处理
 *
 * @author deepin_sir
 */
@Validated
@RequiredArgsConstructor
@RestController
@RequestMapping("/system/post")
public class SysPostController {

    private final SysPostService postService;
    private final SysDeptService deptService;

    /**
     * 获取岗位列表
     */
    @SaCheckPermission("system:post:list")
    @GetMapping("/list")
    public ApiResponse<PageResult<SysPostResp>> list(SysPostReq req) {
        return ApiResponse.ok(postService.selectPagePostList(req));
    }

    /**
     * 导出岗位列表
     */
    @Log(title = "岗位管理", businessType = BusinessType.EXPORT)
    @SaCheckPermission("system:post:export")
    @PostMapping("/export")
    public void export(SysPostReq req, HttpServletResponse response) {
        List<SysPostResp> list = postService.selectPostList(req);
        ExcelUtil.exportExcel(list, "岗位数据", SysPostResp.class, response);
    }

    /**
     * 根据岗位编号获取详细信息
     *
     * @param postId 岗位ID
     */
    @SaCheckPermission("system:post:query")
    @GetMapping(value = "/{postId}")
    public ApiResponse<SysPostResp> get(@PathVariable Long postId) {
        return ApiResponse.ok(postService.selectPostById(postId));
    }

    /**
     * 新增岗位
     */
    @SaCheckPermission("system:post:add")
    @Log(title = "岗位管理", businessType = BusinessType.INSERT)
    @RepeatSubmit()
    @PostMapping
    public ApiResponse<Void> create(@Validated @RequestBody SysPostReq req) {
        if (!postService.checkPostNameUnique(req)) {
            return ApiResponse.fail("新增岗位'" + req.getPostName() + "'失败，岗位名称已存在");
        } else if (!postService.checkPostCodeUnique(req)) {
            return ApiResponse.fail("新增岗位'" + req.getPostName() + "'失败，岗位编码已存在");
        }
        return postService.insertPost(req) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 修改岗位
     */
    @SaCheckPermission("system:post:edit")
    @Log(title = "岗位管理", businessType = BusinessType.UPDATE)
    @RepeatSubmit()
    @PutMapping
    public ApiResponse<Void> update(@Validated @RequestBody SysPostReq req) {
        if (!postService.checkPostNameUnique(req)) {
            return ApiResponse.fail("修改岗位'" + req.getPostName() + "'失败，岗位名称已存在");
        } else if (!postService.checkPostCodeUnique(req)) {
            return ApiResponse.fail("修改岗位'" + req.getPostName() + "'失败，岗位编码已存在");
        } else if (SystemConstants.DISABLE.equals(req.getStatus())
                && postService.countUserPostById(req.getId()) > 0) {
            return ApiResponse.fail("该岗位下存在已分配用户，不能禁用!");
        }
        return postService.updatePost(req) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 删除岗位
     *
     * @param postIds 岗位ID串
     */
    @SaCheckPermission("system:post:remove")
    @Log(title = "岗位管理", businessType = BusinessType.DELETE)
    @DeleteMapping("/{postIds}")
    public ApiResponse<Void> delete(@PathVariable Long[] postIds) {
        return postService.deletePostByIds(Arrays.asList(postIds)) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 获取岗位选择框列表
     *
     * @param postIds 岗位ID串
     * @param deptId  部门id
     */
    @SaCheckPermission("system:post:query")
    @GetMapping("/optionselect")
    public ApiResponse<List<SysPostResp>> optionselect(@RequestParam(required = false) Long[] postIds, @RequestParam(required = false) Long deptId) {
        List<SysPostResp> list = new ArrayList<>();
        if (ObjectUtil.isNotNull(deptId)) {
            SysPostReq req = new SysPostReq();
            req.setDeptId(deptId);
            list = postService.selectPostList(req);
        } else if (postIds != null) {
            list = postService.selectPostByIds(List.of(postIds));
        }
        return ApiResponse.ok(list);
    }

    /**
     * 获取部门树列表
     */
    @SaCheckPermission("system:post:list")
    @GetMapping("/deptTree")
    public ApiResponse<List<Tree<Long>>> deptTree(SysDeptReq req) {
        return ApiResponse.ok(deptService.selectDeptTreeList(req));
    }


}
