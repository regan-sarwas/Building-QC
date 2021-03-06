USE akr_facility;
GO
alter table [gis].[FMSSEXPORT] add CRV2 numeric(15,6);
update [gis].[FMSSEXPORT] set CRV2 = cast(replace(CRV,',','') as numeric(15,6));
alter table [gis].[FMSSEXPORT] drop column CRV;
EXEC sp_rename 'gis.FMSSEXPORT.CRV2', 'CRV', 'COLUMN';
GO