package com.walnut.seed.module.system.controller.system;
import com.walnut.seed.common.core.domain.PageResult;

import cn.dev33.satoken.annotation.SaCheckPermission;
import lombok.RequiredArgsConstructor;
import com.walnut.seed.common.core.domain.ApiResponse;
import com.walnut.seed.common.core.service.DictService;
import com.walnut.seed.common.redis.idempotent.annotation.RepeatSubmit;
import com.walnut.seed.common.log.annotation.Log;
import com.walnut.seed.common.log.enums.BusinessType;
import com.walnut.seed.common.sse.utils.SseMessageUtils;
import com.walnut.seed.module.system.domain.req.SysNoticeReq;
import com.walnut.seed.module.system.domain.resp.SysNoticeResp;
import com.walnut.seed.module.system.service.SysNoticeService;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

/**
 * 公告 信息操作处理
 *
 * @author deepin_sir
 */
@Validated
@RequiredArgsConstructor
@RestController
@RequestMapping("/system/notice")
public class SysNoticeController {

    private final SysNoticeService noticeService;
    private final DictService dictService;

    /**
     * 获取通知公告列表
     */
    @SaCheckPermission("system:notice:list")
    @GetMapping("/list")
    public ApiResponse<PageResult<SysNoticeResp>> list(SysNoticeReq req) {
        return ApiResponse.ok(noticeService.selectPageNoticeList(req));
    }

    /**
     * 根据通知公告编号获取详细信息
     *
     * @param noticeId 公告ID
     */
    @SaCheckPermission("system:notice:query")
    @GetMapping(value = "/{noticeId}")
    public ApiResponse<SysNoticeResp> get(@PathVariable Long noticeId) {
        return ApiResponse.ok(noticeService.selectNoticeById(noticeId));
    }

    /**
     * 新增通知公告
     */
    @SaCheckPermission("system:notice:add")
    @Log(title = "通知公告", businessType = BusinessType.INSERT)
    @RepeatSubmit()
    @PostMapping
    public ApiResponse<Void> create(@Validated @RequestBody SysNoticeReq req) {
        int rows = noticeService.insertNotice(req);
        if (rows <= 0) {
            return ApiResponse.fail();
        }
        String type = dictService.getDictLabel("sys_notice_type", req.getNoticeType());
        SseMessageUtils.publishAll("[" + type + "] " + req.getNoticeTitle());
        return ApiResponse.ok();
    }

    /**
     * 修改通知公告
     */
    @SaCheckPermission("system:notice:edit")
    @Log(title = "通知公告", businessType = BusinessType.UPDATE)
    @RepeatSubmit()
    @PutMapping
    public ApiResponse<Void> update(@Validated @RequestBody SysNoticeReq req) {
        return noticeService.updateNotice(req) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }

    /**
     * 删除通知公告
     *
     * @param noticeIds 公告ID串
     */
    @SaCheckPermission("system:notice:remove")
    @Log(title = "通知公告", businessType = BusinessType.DELETE)
    @DeleteMapping("/{noticeIds}")
    public ApiResponse<Void> delete(@PathVariable Long[] noticeIds) {
        return noticeService.deleteNoticeByIds(noticeIds) > 0 ? ApiResponse.ok() : ApiResponse.fail();
    }
}
