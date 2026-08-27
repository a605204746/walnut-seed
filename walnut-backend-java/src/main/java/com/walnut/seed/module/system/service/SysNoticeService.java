package com.walnut.seed.module.system.service;
import com.walnut.seed.common.core.domain.PageResult;

import com.walnut.seed.module.system.domain.req.SysNoticeReq;
import com.walnut.seed.module.system.domain.resp.SysNoticeResp;

import java.util.List;

/**
 * 公告 服务层
 *
 * @author deepin_sir
 */
public interface SysNoticeService {

    /**
     * 分页查询通知公告列表
     *
     * @param notice    查询条件
     * @param pageQuery 分页参数
     * @return 通知公告分页列表
     */
    PageResult<SysNoticeResp> selectPageNoticeList(SysNoticeReq req);

    /**
     * 查询公告信息
     *
     * @param noticeId 公告ID
     * @return 公告信息
     */
    SysNoticeResp selectNoticeById(Long noticeId);

    /**
     * 查询公告列表
     *
     * @param notice 公告信息
     * @return 公告集合
     */
    List<SysNoticeResp> selectNoticeList(SysNoticeReq notice);

    /**
     * 新增公告
     *
     * @param req 公告信息
     * @return 结果
     */
    int insertNotice(SysNoticeReq req);

    /**
     * 修改公告
     *
     * @param req 公告信息
     * @return 结果
     */
    int updateNotice(SysNoticeReq req);

    /**
     * 删除公告信息
     *
     * @param noticeId 公告ID
     * @return 结果
     */
    int deleteNoticeById(Long noticeId);

    /**
     * 批量删除公告信息
     *
     * @param noticeIds 需要删除的公告ID
     * @return 结果
     */
    int deleteNoticeByIds(Long[] noticeIds);
}
