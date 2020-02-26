USAGE = """

 Creates a Tableau Data Extract for validating roadway volumes compared to PeMS or CalTrans count data.

 Input:
========
1) .\avgload5period.csv: model data
   Required columns: a, b, lanes, volEA_tot, volAM_tot, volMD_tot, volPM_tot, volEV_tot

If PeMS years specified:

p2) M:\Crosswalks\PeMSStations_TM1network\crosswalk_2015.csv: maps model roadway links to PeMS stations
    Required columns: a, b, station, HOV

p3) (Box: Share Data\pems-typical-weekday\pems_period.csv): PeMS observed data, generated by
    https://github.com/MetropolitanTransportationCommission/pems-typical-weekday
    Required columns: station, route, direction, time_period, 
                      lanes, median_flow, avg_flow, abs_pm, latitude, longitude, year

If CalTrans years specified:

c2) model_to_caltrans.csv: maps model roadway links to CalTrans count locations
    Required columns: a, b, county, route, postmile, direction, leg, description

c3) (Box: Share Data\caltrans-typical-weekday\typical-weekday-counts.csv): CalTrans observed data,
    generated by https://github.com/BayAreaMetro/caltrans-typical-weekday-counts

Output:
========

If PeMS years specified:

p1) Roadways to PeMS.[csv,tde]: dataframe containing both modeled and observed data where each row is one volume
    (e.g. observed OR modeled)

    Columns: a, b, A_B, at, ft, county, sep_HOV,                              (model link)
             district, station, route, direction, type,                       (PeMS station)
             abs_pm, latitude, longitude,                                     (PeMS station location)
             link_count, pemsonlink, distlink, lanes match,                   (matching info)
             time_period, lanes, volume, category                             (volumes)
    Where category is one of [(year) Modeled, (year) Observed]

    Note: PeMS data without model links are in this dataset with a,b=-1

p2) Roadways to PeMS_wide.[csv,tde]: dataframe containing both modeled and observed data where each row is one set
    of volumes (observed AND modeled)

    Columns: a, b, A_B, at, ft, county, sep_HOV, lanes modeled,               (model link)
             district, station, route, direction, type, lanes observed,       (PeMS station)
             abs_pm, latitude, longitude,                                     (PeMS station location)
             link_count, pemsonlink, distlink, lanes match,                   (matching info)
             time_period, 2015 Modeled, 2014 Observed, 2015 Observed, 2016 Observed, Average Observed


If CalTrans years specified:

"""
import argparse, os, sys
import numpy, pandas
import dataextract as tde

TM_HOV_TO_GP_FILE   = "M:\Crosswalks\PeMSStations_TM1network\hov_to_gp_links.csv"
PEMS_MAP_FILE       = "M:\Crosswalks\PeMSStations_TM1network\crosswalk_2015.csv"
CALTRANS_MAP_FILE   = "M:\Crosswalks\CaltransCountLocations_TM1network\\typical-weekday-counts-xy-TM1link.csv"
MODEL_FILE          = "avgload5period.csv"
SHARE_DATA          = os.path.join(os.environ["USERPROFILE"], "Box", "Modeling and Surveys", "Share Data")
PEMS_FILE           = os.path.join(SHARE_DATA, "pems-typical-weekday", "pems_period.csv")
CALTRANS_FILE       = os.path.join(SHARE_DATA, "caltrans-typical-weekday", "typical-weekday-counts.csv")
PEMS_OUTPUT_FILE    = "Roadways to PeMS"
CALTRANS_OUTPUT_FILE= "Roadways to Caltrans"

MODEL_COLUMNS       = ['a','b','ft','at','county','lanes','volEA_tot','volAM_tot','volMD_tot','volPM_tot','volEV_tot']
PEMS_COLUMNS        = ['station','route','direction','time_period','lanes','avg_flow','abs_pm','latitude','longitude','year']

fieldMap = {
    'float64' :     tde.Type.DOUBLE,
    'float32' :     tde.Type.DOUBLE,
    'int64' :       tde.Type.DOUBLE,
    'int32' :       tde.Type.DOUBLE,
    'object':       tde.Type.UNICODE_STRING,
    'bool' :        tde.Type.BOOLEAN
}

# these are bad crosswalk
PEMS_BAD_STATION_CROSSWALK = [401819, 401820]

# 
# from Rdata to TableauExtract.py -- move to library?
# 
def write_tde(table_df, tde_fullpath, arg_append):
    """
    Writes the given pandas dataframe to the Tableau Data Extract given by tde_fullpath
    """
    if arg_append and not os.path.isfile(tde_fullpath):
        print "Couldn't append -- file doesn't exist"
        arg_append = False

    # Remove it if already exists
    if not arg_append and os.path.exists(tde_fullpath):
        os.remove(tde_fullpath)
    tdefile = tde.Extract(tde_fullpath)

    # define the table definition
    table_def = tde.TableDefinition()

    # create a list of column names
    colnames = table_df.columns
    # create a list of column types
    coltypes = table_df.dtypes

    # for each column, add the appropriate info the Table Definition
    for col_idx in range(0, len(colnames)):
        cname = colnames[col_idx]
        ctype = fieldMap[str(coltypes[col_idx])]
        table_def.addColumn(cname, ctype)

    # create the extract from the Table Definition
    if arg_append:
        tde_table = tdefile.openTable('Extract')
    else:
        tde_table = tdefile.addTable('Extract', table_def)
    row = tde.Row(table_def)

    isnull_df = pandas.isnull(table_df)
    # print isnull_df.head()

    for r in range(0, table_df.shape[0]):
        for c in range(0, len(coltypes)):
            try:
                if isnull_df.iloc[r,c]==True:
                    row.setNull(c)
                elif str(coltypes[c]) == 'float64':
                    row.setDouble(c, table_df.iloc[r,c])
                elif str(coltypes[c]) == 'float32':
                    row.setDouble(c, table_df.iloc[r,c])
                elif str(coltypes[c]) == 'int64':
                    row.setDouble(c, table_df.iloc[r,c])
                elif str(coltypes[c]) == 'int32':
                    row.setDouble(c, table_df.iloc[r,c])
                elif str(coltypes[c]) == 'object':
                    row.setString(c, str(table_df.iloc[r,c]))
                elif str(coltypes[c]) == 'bool':
                    row.setBoolean(c, table_df.iloc[r,c])
                else:
                    row.setNull(c)
            except:
                print coltypes[c], colnames[c], table_df.iloc[r,c]
                print table_df.iloc[r,:]
                print isnull_df.iloc[r,:]
                raise

        # insert the row
        tde_table.insert(row)

    tdefile.close()
    print "Wrote {} lines to {} with columns {}".format(len(table_df), tde_fullpath, colnames)

if __name__ == '__main__':

    pandas.options.display.width    = 1000
    pandas.options.display.max_rows = 1000
    pandas.options.display.max_columns = 25

    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-m","--model_year",    type=int, required=True)
    parser.add_argument("-c","--caltrans_year", type=int, nargs='*')
    parser.add_argument("-p","--pems_year",     type=int, nargs='*')
    args = parser.parse_args()
    if not args.caltrans_year and not args.pems_year:
        print USAGE
        print "No PeMS year nor CalTrans count year argument specified."
        sys.exit()
    if args.caltrans_year and args.pems_year:
        print USAGE
        print "Please specify pems_year OR caltrans_year but not both"
    print(args)

    ############ read the mapping first
    mapping_df = None
    tde_file   = None
    obs_cols   = []
    if args.pems_year:
        mapping_df = pandas.read_csv(PEMS_MAP_FILE)
        tde_file   = PEMS_OUTPUT_FILE
        obs_cols   = ["{} Observed".format(year) for year in args.pems_year]
    else:
        mapping_df = pandas.read_csv(CALTRANS_MAP_FILE)
        mapping_df.rename(columns={"postmileValue":"post_mile", "routeNumber":"route"}, inplace=True)
        tde_file   = CALTRANS_OUTPUT_FILE
        obs_cols   = ["{} Observed".format(year) for year in args.caltrans_year]

    # column name for model year observed
    modelyear_observed = "{} Observed".format(args.model_year)

    ############ read the model data
    model_df = pandas.read_csv(MODEL_FILE)

    # strip the column names
    col_rename = {}
    for colname in model_df.columns.values.tolist(): col_rename[colname] = colname.strip()
    model_df.rename(columns=col_rename, inplace=True)
    model_df.rename(columns={"gl":"county"}, inplace=True)

    # select only the columns we want
    model_df = model_df[MODEL_COLUMNS]

    # add a daily column
    model_df['Daily'] = model_df[['volEA_tot','volAM_tot','volMD_tot','volPM_tot','volEV_tot']].sum(axis=1)

    # the model data has a, b, lanes, vol*
    # but some of these links are HOV links and the volums should be summed to the same link as the non-hov link
    # read the hov -> gp mapping
    model_hov_to_gp_df = pandas.read_csv(TM_HOV_TO_GP_FILE)
    # keep only those where we succeeded finding GP for now
    model_hov_to_gp_df = model_hov_to_gp_df.loc[ model_hov_to_gp_df.A_B_GP != "NA_NA"]
    # print(model_hov_to_gp_df.head())
    #        A      B  LANES  USE  FT  ROUTENUM ROUTEDIR    A_GP    B_GP         A_B     A_B_GP
    # 10  8900   8901      1    3   2       880        S  3400.0  3399.0   8900_8901  3400_3399
    # 12  8903   8904      1    3   2       880        S  3396.0  3416.0   8903_8904  3396_3416
    # 13  8904   8905      1    3   2       880        S  3416.0  3606.0   8904_8905  3416_3606
    # 14  8905  20229      1    3   2       880        S  3606.0  3603.0  8905_20229  3606_3603
    # 15  8907  20231      1    3   2       880        S  3601.0  3640.0  8907_20231  3601_3640

    # remove me eventually - compensate for bug where HOV link on bridge has wrong county coded
    # https://github.com/BayAreaMetro/TM1_2015_Base_Network/commit/8ecb3cae55616f7ac6fb2ebb2a3f134bd239a13d
    model_df.loc[ (model_df.a==20294)&(model_df.b==10601), "county"] = 5
    model_df.loc[ (model_df.a==10601)&(model_df.b==10607), "county"] = 5

    # join the model data to the hov -> gp mapping
    model_df = pandas.merge(left   =model_df,  right   =model_hov_to_gp_df[["A","B","LANES","USE","A_GP","B_GP"]],
                            left_on=["a","b"], right_on=["A","B"],
                            how    ="left")
    # print("model_df hov links head\n{}".format(model_df.loc[ pandas.notnull(model_df.A_GP)].head()))
    # set those to HOV true and set the a,b to the GP versions
    model_df["sep_HOV"] = False
    model_df.loc[ pandas.notnull(model_df.A_GP), "sep_HOV"] = True
    model_df.loc[ pandas.notnull(model_df.A_GP), "a"      ] = model_df.A_GP
    model_df.loc[ pandas.notnull(model_df.A_GP), "b"      ] = model_df.B_GP
    # drop other cols and make a,b back into int
    model_df = model_df[ MODEL_COLUMNS + ["Daily", "sep_HOV"]]
    model_df["a"] = model_df["a"].astype(int)
    model_df["b"] = model_df["b"].astype(int)
    # now a,b isn't unique so group
    model_df["link_count"] = 1
    model_df = model_df.groupby(["a","b","at","ft","county"]).agg(sum).reset_index()
    print("model_df head\n{}".format(model_df.loc[model_df.link_count>1].head()))

    # create a multi index for stacking
    model_df.set_index(['a','b','ft','at','county','lanes','sep_HOV','link_count'], inplace=True)
    # stack: so now we have a series with multiindex: a,b,lanes,varname
    model_df = pandas.DataFrame({'volume': model_df.stack()})
    # reset the index
    model_df.reset_index(inplace=True)
    print("model_df head\n{}".format(model_df.head(12)))

    # and rename it
    model_df.rename(columns={'level_8':'time_period'}, inplace=True)
    # remove extra chars: 'volAM_tot' => 'AM'
    model_df.loc[model_df['time_period']!='Daily','time_period'] = model_df['time_period'].str[3:5]
    print("model_df head\n{}".format(model_df.head(12)))

    if args.pems_year:
        ############ read the pems data
        obs_df = pandas.read_csv(PEMS_FILE, na_values='NA', engine='python')

        # select only the columns we want
        obs_df = obs_df[PEMS_COLUMNS]
        # select only the years in question
        obs_df = obs_df[ obs_df['year'].isin(args.pems_year)].reset_index(drop=True)

        # create missing cols in PeMS
        obs_df.rename(columns={'avg_flow':'volume', 'year':'category'}, inplace=True)
        print("obs_df len={} head\n{}".format(len(obs_df), obs_df.head(22)))
        #    station  route direction time_period  lanes        volume   abs_pm   latitude   longitude  category
        #0    400001    101         N          AM      5  23462.250000  387.897  37.364085 -121.901149      2014
        #1    400001    101         N          EA      5   7549.107143  387.897  37.364085 -121.901149      2014
        #2    400001    101         N          EV      5   9162.789474  387.897  37.364085 -121.901149      2014
        #3    400001    101         N          MD      5  18982.450000  387.897  37.364085 -121.901149      2014
        #4    400001    101         N          PM      5  11771.904762  387.897  37.364085 -121.901149      2014

        obs_daily_df = obs_df.groupby(["station","route","direction","lanes","category","abs_pm","longitude","latitude"]).aggregate({"time_period":"count","volume":"sum"})
        obs_daily_df.reset_index(inplace=True)
        assert(len(obs_daily_df.loc[obs_daily_df.time_period>5])==0)
        # drop those with fewer than 5 time periods
        obs_daily_df = obs_daily_df.loc[ obs_daily_df.time_period == 5 ]
        assert( len(obs_daily_df.loc[obs_daily_df.time_period!=5])==0 )
        # add these
        obs_daily_df["time_period"] = "Daily"
        obs_df = pandas.concat([obs_df, obs_daily_df], axis="index", sort=True) # sort means sort columns first so they are aligned
        obs_df.sort_values(by=["station","route","direction","lanes","category","time_period"], inplace=True)
        obs_df.reset_index(drop=True, inplace=True)
        print("obs_df len={} head\n{}".format(len(obs_df), obs_df.head(22)))

        #      abs_pm  category direction  lanes   latitude   longitude  route  station time_period         volume
        # 0   387.897      2014         N      5  37.364085 -121.901149    101   400001          AM   23462.250000
        # 1   387.897      2014         N      5  37.364085 -121.901149    101   400001       Daily   70928.501378
        # 2   387.897      2014         N      5  37.364085 -121.901149    101   400001          EA    7549.107143
        # 3   387.897      2014         N      5  37.364085 -121.901149    101   400001          EV    9162.789474
        # 4   387.897      2014         N      5  37.364085 -121.901149    101   400001          MD   18982.450000
        # 5   387.897      2014         N      5  37.364085 -121.901149    101   400001          PM   11771.904762
        obs_df['category'] = obs_df.category.map(str) + ' Observed'

        # want to bring category into columns
        obs_wide = pandas.pivot_table(obs_df, values="volume", index=["station","route","direction","abs_pm","latitude","longitude","lanes","time_period"], columns="category")
        obs_wide["Average Observed"] = obs_wide.mean(axis=1)  # this will not include NaNs or missing vals so it handles them correctly
        obs_wide.reset_index(inplace=True)

        print("obs_wide head\n{}".format(obs_wide.head(12)))
        # category  station  route direction   abs_pm       ...         2014 Observed  2015 Observed  2016 Observed Average Observed
        # 0          400001    101         N  387.897       ...          23462.250000   22879.842857   22948.736111     23096.942989
        # 1          400001    101         N  387.897       ...          70928.501378   72694.426221   72613.167349     72078.698316
        # 2          400001    101         N  387.897       ...           7549.107143    8072.062500    8537.581081      8052.916908
        # 3          400001    101         N  387.897       ...           9162.789474    9398.333333    9323.211268      9294.778025
        # 4          400001    101         N  387.897       ...          18982.450000   20523.112903   20314.888889     19940.150597
        # 5          400001    101         N  387.897       ...          11771.904762   11821.074627   11488.750000     11693.909796
        # 6          400002    101         S  416.893       ...          25756.980769            NaN            NaN     25756.980769
        # 7          400002    101         S  416.893       ...         117650.026125            NaN            NaN    117650.026125
        # 8          400002    101         S  416.893       ...           4034.363636            NaN            NaN      4034.363636
        # 9          400002    101         S  416.893       ...          26445.960000            NaN            NaN     26445.960000
        # 10         400002    101         S  416.893       ...          32385.192308            NaN            NaN     32385.192308
        # 11         400002    101         S  416.893       ...          29027.529412            NaN            NaN     29027.529412
    else:
        ############ read the caltrans data
        obs_df = pandas.read_csv(CALTRANS_FILE)
        print("Read {} rows from {}. head:\n{}".format(len(obs_df), CALTRANS_FILE, obs_df.head()))

        # make columns conform to previous version and to model data
        obs_df.rename(columns={"county":"countyCode"}, inplace=True)

        # select the relevant years
        obs_df = obs_df.loc[ obs_df.year.isin(args.caltrans_year)]

        # add station,description column to mapping_df -- and keep only the relevant entries since mapping_df includes stations for all years
        description_df = obs_df[["route","countyCode","post_mile","direction","station","description"]].drop_duplicates()
        print("locations with descriptions ({}) head:\n{}".format(len(description_df), description_df.head()))
        mapping_df = pandas.merge(left=mapping_df, right=description_df, how="inner")

        id_vars = ["route","countyCode","post_mile","leg","direction","station","description"]

        # set the time_period
        obs_df["time_period"] = "EV"
        obs_df.loc[(obs_df.integer_hour >=  3)&(obs_df.integer_hour <  6), "time_period"] = "EA"
        obs_df.loc[(obs_df.integer_hour >=  6)&(obs_df.integer_hour < 10), "time_period"] = "AM"
        obs_df.loc[(obs_df.integer_hour >= 10)&(obs_df.integer_hour < 15), "time_period"] = "MD"
        obs_df.loc[(obs_df.integer_hour >= 15)&(obs_df.integer_hour < 19), "time_period"] = "PM"

        # aggregate to time period and verify each is complete
        obs_df = obs_df.groupby(id_vars + ["year","time_period"]).aggregate(
            {"integer_hour":"count", "median_count":"sum", "avg_count":"sum", "days_observed":"mean"}).reset_index()
        print("obs_df len={} head\n{}".format(len(obs_df), obs_df.head(10)))

        obs_df = obs_df.loc[ ((obs_df.time_period=="EA")&(obs_df.integer_hour==3))|
                             ((obs_df.time_period=="AM")&(obs_df.integer_hour==4))|
                             ((obs_df.time_period=="MD")&(obs_df.integer_hour==5))|
                             ((obs_df.time_period=="PM")&(obs_df.integer_hour==4))|
                             ((obs_df.time_period=="EV")&(obs_df.integer_hour==8))]
        print("obs_df len={} head\n{}".format(len(obs_df), obs_df.head(10)))

        # drop integer_hour count, median_count, days_observed -- retain sum of avg_count as the volume
        obs_df.drop(columns=["integer_hour","median_count","days_observed"], inplace=True)
        obs_df.rename(columns={"avg_count":"volume"}, inplace=True)
        print("obs_df len={} head\n{}".format(len(obs_df), obs_df.head(10)))

        # get Daily by year and add it
        obs_daily_df = obs_df.groupby(id_vars + ["year"]).aggregate({"time_period":"count","volume":"sum"})
        # drop any that are incomplete
        print("Dropping {} obs_daily_df rows for being incomplete".format(len(obs_daily_df.loc[obs_daily_df.time_period != 5])))
        obs_daily_df = obs_daily_df.loc[obs_daily_df.time_period==5]
        obs_daily_df["time_period"] = "Daily"
        obs_daily_df.reset_index(inplace=True)
        print("obs_daily_df len={} head\n{}".format(len(obs_daily_df), obs_daily_df.head()))
        #    route countyCode  post_mile leg direction  station                     description  year time_period        volume
        # 0      4         CC       11.4   B         E    912.0                    PACHECO BLVD  2016       Daily  41295.952381
        # 1      4         CC       11.4   B         W    912.0                    PACHECO BLVD  2016       Daily  45729.761905
        # 2     12        NAP        2.3   B         E    906.0  .2-MI N/O NAPA/SOLANO COUNTY L  2014       Daily  18502.722816
        # 3     12        NAP        2.3   B         E    906.0  .2-MI N/O NAPA/SOLANO COUNTY L  2015       Daily  19656.101695
        # 4     12        NAP        2.3   B         E    906.0  .2-MI N/O NAPA/SOLANO COUNTY L  2016       Daily  20468.062500
        obs_df = pandas.concat([obs_df, obs_daily_df], axis="index", sort=True) # sort means sort columns first so they are aligned
        obs_df['category'] = obs_df.year.map(str) + ' Observed'
        obs_df.drop(columns=["year"], inplace=True)
        print("obs_df len={} head\n{}".format(len(obs_df), obs_df.head()))

        # move category (year) to columns
        obs_wide = pandas.pivot_table(obs_df, index=id_vars + ["time_period"], columns=["category"], values="volume")
        obs_wide["Average Observed"] = obs_wide.mean(axis=1)  # this will not include NaNs or missing vals so it handles them correctly
        obs_wide.reset_index(inplace=True)
        print("obs_wide len={} head\n{}".format(len(obs_wide), obs_wide.head()))

    # model has a, b, A_B
    obs_df['a'] = -1
    obs_df['b'] = -1
    obs_df['A_B'] = ""

    # create the final stacked table -- first the model information
    mapping_df.rename(columns={"A":"a", "B":"b"}, inplace=True)
    print("mapping_df head\n{}".format(mapping_df.head()))
    #    station  district  route direction type   latitude   longitude     a     b  distlink        A_B
    # 0   400001         4    101         N   ML  37.364085 -121.901149  5716  5690  0.000855  5716_5690
    # 1   400006         4    880         S   ML  37.605003 -122.065542  3715  3712  0.001245  3715_3712
    # 2   400007         4    101         N   ML  37.586936 -122.337721  6315  6409  0.001026  6315_6409
    # 3   400009         4     80         W   ML  37.864883 -122.303345  2512  2509  0.000422  2512_2509
    # 4   400010         4    101         N   ML  37.629765 -122.402365  6554  6567  0.000303  6554_6567
    # print("mapping_df cols:\n{}\nmodel_df cols:\n{}".format(mapping_df.dtypes, model_df.dtypes))
    model_final_df = pandas.merge(left=mapping_df, right=model_df, how='inner')
    model_final_df['category'] = '%d Modeled' % args.model_year
    print("model_final_df head\n{}".format(model_final_df.head(12)))

    # model_final_df head - pems
    #     station  district  route direction type   latitude   longitude     a     b  distlink        A_B  lanes  sep_HOV  link_count time_period    volume      category
    # 0    400001         4    101         N   ML  37.364085 -121.901149  5716  5690  0.000855  5716_5690    4.0     True           2          EA   4316.77  2015 Modeled
    # 1    400001         4    101         N   ML  37.364085 -121.901149  5716  5690  0.000855  5716_5690    4.0     True           2          AM  23606.98  2015 Modeled
    # 2    400001         4    101         N   ML  37.364085 -121.901149  5716  5690  0.000855  5716_5690    4.0     True           2          MD  18513.31  2015 Modeled
    # 3    400001         4    101         N   ML  37.364085 -121.901149  5716  5690  0.000855  5716_5690    4.0     True           2          PM  12764.99  2015 Modeled
    # 4    400001         4    101         N   ML  37.364085 -121.901149  5716  5690  0.000855  5716_5690    4.0     True           2          EV   5765.52  2015 Modeled
    # 5    400001         4    101         N   ML  37.364085 -121.901149  5716  5690  0.000855  5716_5690    4.0     True           2       Daily  64967.57  2015 Modeled
    # 6    400006         4    880         S   ML  37.605003 -122.065542  3715  3712  0.001245  3715_3712    4.0     True           2          EA   5642.29  2015 Modeled
    # 7    400006         4    880         S   ML  37.605003 -122.065542  3715  3712  0.001245  3715_3712    4.0     True           2          AM  25418.81  2015 Modeled
    # 8    400006         4    880         S   ML  37.605003 -122.065542  3715  3712  0.001245  3715_3712    4.0     True           2          MD  23771.06  2015 Modeled
    # 9    400006         4    880         S   ML  37.605003 -122.065542  3715  3712  0.001245  3715_3712    4.0     True           2          PM  24153.04  2015 Modeled
    # 10   400006         4    880         S   ML  37.605003 -122.065542  3715  3712  0.001245  3715_3712    4.0     True           2          EV  18160.92  2015 Modeled
    # 11   400006         4    880         S   ML  37.605003 -122.065542  3715  3712  0.001245  3715_3712    4.0     True           2       Daily  97146.12  2015 Modeled

    # model_final_df head - caltrans
    #      latitude   longitude countyCode  post_mile  route direction postmileSuffix  link_rowid     a     b  dist_from_link        A_B  ft  at  county  lanes  sep_HOV  link_count time_period    volume      category
    # 0   37.854479 -122.218076        ALA      5.887     24         E              R         143  1952  1950    4.228366e+06  1952_1950   1   3       5    3.0    False           1          EA   2287.43  2015 Modeled
    # 1   37.854479 -122.218076        ALA      5.887     24         E              R         143  1952  1950    4.228366e+06  1952_1950   1   3       5    3.0    False           1          AM   8742.13  2015 Modeled
    # 2   37.854479 -122.218076        ALA      5.887     24         E              R         143  1952  1950    4.228366e+06  1952_1950   1   3       5    3.0    False           1          MD  14216.70  2015 Modeled
    # 3   37.854479 -122.218076        ALA      5.887     24         E              R         143  1952  1950    4.228366e+06  1952_1950   1   3       5    3.0    False           1          PM  17774.32  2015 Modeled
    # 4   37.854479 -122.218076        ALA      5.887     24         E              R         143  1952  1950    4.228366e+06  1952_1950   1   3       5    3.0    False           1          EV  14894.33  2015 Modeled
    # 5   37.854479 -122.218076        ALA      5.887     24         E              R         143  1952  1950    4.228366e+06  1952_1950   1   3       5    3.0    False           1       Daily  57914.91  2015 Modeled
    # 6   37.854479 -122.218076        ALA      5.887     24         W              L         126  1917  1915    4.228366e+06  1917_1915   1   3       5    3.0    False           1          EA   3557.25  2015 Modeled
    # 7   37.854479 -122.218076        ALA      5.887     24         W              L         126  1917  1915    4.228366e+06  1917_1915   1   3       5    3.0    False           1          AM  21925.53  2015 Modeled
    # 8   37.854479 -122.218076        ALA      5.887     24         W              L         126  1917  1915    4.228366e+06  1917_1915   1   3       5    3.0    False           1          MD  16331.60  2015 Modeled
    # 9   37.854479 -122.218076        ALA      5.887     24         W              L         126  1917  1915    4.228366e+06  1917_1915   1   3       5    3.0    False           1          PM  15007.88  2015 Modeled
    # 10  37.854479 -122.218076        ALA      5.887     24         W              L         126  1917  1915    4.228366e+06  1917_1915   1   3       5    3.0    False           1          EV   8425.77  2015 Modeled
    # 11  37.854479 -122.218076        ALA      5.887     24         W              L         126  1917  1915    4.228366e+06  1917_1915   1   3       5    3.0    False           1       Daily  65248.03  2015 Modeled
    print("Model columns: {}".format(sorted(model_final_df.columns.values.tolist())))
    print("Obsrv columns: {}".format(sorted(obs_df.columns.values.tolist())))
    print("Obs_wide columns: {}".format(sorted(obs_wide.columns.values.tolist())))
    # followed by the observed
    table_df = pandas.concat([model_final_df, obs_df], axis="index", sort=True) # sort means sort columns first so they are aligned

    # want a "wide" version, with a column for obsy1, obsy2, obsy3, modeled

    if args.caltrans_year:
        index_cols = ["countyCode","route","post_mile","direction","time_period"]
    else:
        index_cols = ["station","route","direction","abs_pm","latitude","longitude","time_period"]

    model_wide = model_final_df[index_cols + ["a","b","A_B","ft","at","county","sep_HOV","link_count", "stationsonlink", "distlink", "lanes","volume"]].copy()
    model_wide.rename(columns={"volume":"{} Modeled".format(args.model_year), 
                               "lanes":"lanes modeled"}, inplace=True)

    obs_wide.reset_index(inplace=True)
    obs_wide.rename(columns={"lanes":"lanes observed"}, inplace=True)
    print("obs_wide head\n{}".format(obs_wide.head()))


    # the wide table is an inner join
    table_wide = pandas.merge(left=model_wide, right=obs_wide, how='inner', on=index_cols)
    print("table_wide head\n{}".format(table_wide.head()))

    if args.pems_year:
        # add lanes match attribute
        table_wide['lanes match'] = 0
        table_wide.loc[ table_wide['lanes modeled'] == table_wide['lanes observed'], 'lanes match'] = 1
    else:
        # no data for caltrans so assume match
        table_wide['lanes match'] = 1

    ### filter down to max of one station per link by adding columns "skip", "skip_reason"
    # iterate through links by time period whittle down to a single observed for each link
    # store results here. columns = A_B, time_period, station, skip, skip_reason
    AB_timeperiod_station = pandas.DataFrame()

    for AB_timeperiod,group_orig in table_wide.groupby(["A_B","time_period"]):
        print("Processing {}".format(AB_timeperiod))
        group = group_orig.copy() # to make it clear

        group["skip"       ] = 0
        group["skip_reason"] = ""

        # skip due to lanes mismatch
        group.loc[ (group.skip==0)&(group["lanes match"]== 0), "skip_reason"] = "lanes mismatch"
        group.loc[ (group.skip==0)&(group["lanes match"]== 0), "skip"       ] = 1

        useable = len(group)-group.skip.sum()
        print("  Group has length {} and skips {} with {} remaining as useable ".format(len(group), group.skip.sum(), useable))
        if useable <= 1: 
            AB_timeperiod_station = pandas.concat([AB_timeperiod_station, 
                                                   group[["A_B","time_period","station","skip","skip_reason"]]])
            continue

        # if there are some with modelyear observed and some without, kick out the ones without
        obs_target_notnull = group.loc[ (group.skip==0)&pandas.notnull(group[modelyear_observed]) ]
        obs_target_isnull  = group.loc[ (group.skip==0)&pandas.isnull(group[modelyear_observed])  ]
        if len(obs_target_notnull) > 0 and len(obs_target_isnull) > 0:
            print("  Skipping {} rows due to null {}".format(len(obs_target_isnull), modelyear_observed))
            group.loc[ (group.skip==0)&pandas.isnull(group[modelyear_observed]), "skip_reason" ] = "{} null".format(modelyear_observed)
            group.loc[ (group.skip==0)&pandas.isnull(group[modelyear_observed]), "skip"        ] = 1

            useable = len(group)-group.skip.sum()
            print("  Group has length {} and skips {} with {} remaining as useable ".format(len(group), group.skip.sum(), useable))
            if useable <= 1: 
                AB_timeperiod_station = pandas.concat([AB_timeperiod_station, 
                                                       group[["A_B","time_period","station","skip","skip_reason"]]])
                continue

        # if there are some with more observed, kick out the ones with fewer
        group["obs_count"] = 0
        for obs_col in obs_cols: group.loc[ pandas.notnull(group[obs_col]), "obs_count"] += 1
        max_obs_count   = group.loc[ group.skip==0, "obs_count"].max()
        fewer_obs_count = group.loc[ (group.skip==0)&(group.obs_count < max_obs_count) ]
        if len(fewer_obs_count) > 0:
            print("  Skipping {} rows due to having fewer observations than {}".format(len(fewer_obs_count), max_obs_count))
            group.loc[ (group.skip==0)&(group.obs_count < max_obs_count), "skip_reason"] = "fewer observations than {}".format(max_obs_count)
            group.loc[ (group.skip==0)&(group.obs_count < max_obs_count), "skip"       ] = 1

            useable = len(group)-group.skip.sum()
            print("  Group has length {} and skips {} with {} remaining as useable ".format(len(group), group.skip.sum(), useable))
            if useable <= 1: 
                AB_timeperiod_station = pandas.concat([AB_timeperiod_station, 
                                                       group[["A_B","time_period","station","skip","skip_reason"]]])
                continue

        # if there are more than two remaining, use distlink to break the tie
        # todo: it would be preferable to choose the median daily value or closest to the middle of the link but those are more work
        min_distlink    = group.loc[ group.skip==0, "distlink"].min()
        bigger_distlink = group.loc[ (group.skip==0)&(group.distlink > min_distlink) ]
        if len(bigger_distlink) > 0:
            print("  Skipping {} rows due to having bigger distlink than {}".format(len(bigger_distlink), min_distlink))
            group.loc[ (group.skip==0)&(group.distlink > min_distlink), "skip_reason"] = "bigger distlink than {}".format(min_distlink)
            group.loc[ (group.skip==0)&(group.distlink > min_distlink), "skip"       ] = 1

            useable = len(group)-group.skip.sum()
            print("  Group has length {} and skips {} with {} remaining as useable ".format(len(group), group.skip.sum(), useable))
            if useable <= 1: 
                AB_timeperiod_station = pandas.concat([AB_timeperiod_station, 
                                                       group[["A_B","time_period","station","skip","skip_reason"]]])
                continue

        # if min distlink didn't do it, use station number to break the tie (yes, this happens)
        min_station    = group.loc[ group.skip==0, "station"].min()
        bigger_station = group.loc[ (group.skip==0)&(group.station > min_station) ]
        if len(bigger_station) > 0:
            print("  Skipping {} rows arbitrarily (station num) {}".format(len(bigger_distlink), min_distlink))
            group.loc[ (group.skip==0)&(group.station > min_station), "skip_reason"] = "random (non-min station)"
            group.loc[ (group.skip==0)&(group.station > min_station), "skip"       ] = 1

            useable = len(group)-group.skip.sum()
            print("  Group has length {} and skips {} with {} remaining as useable ".format(len(group), group.skip.sum(), useable))
            if useable <= 1: 
                AB_timeperiod_station = pandas.concat([AB_timeperiod_station, 
                                                       group[["A_B","time_period","station","skip","skip_reason"]]])
                continue

        # this shouldn't happen -- but it's useful when constructing above logic
        print(group)
        print(group[["A_B","station","distlink","skip","skip_reason"]])
        value = raw_input("Type any key to continue...\n")
        break

    # purge observed data with known bad crosswalk
    if args.pems_year:
        AB_timeperiod_station.loc[ AB_timeperiod_station.station.isin(PEMS_BAD_STATION_CROSSWALK), "skip_reason" ] = "known bad crosswalk"
        AB_timeperiod_station.loc[ AB_timeperiod_station.station.isin(PEMS_BAD_STATION_CROSSWALK), "skip"        ] = 1

    # brink skip, skip_reason back to table_wide
    print(AB_timeperiod_station.head())
    table_wide = pandas.merge(left=table_wide, right=AB_timeperiod_station, how="left")
    print(table_wide.head())

    # bring the attributes "lanes match", "county", "skip", "skip_reason" back to non-wide table
    lanes_match_df = table_wide[index_cols + ["lanes match","county","skip","skip_reason"]].drop_duplicates()
    print("lanes_match_df head:\n{}".format(lanes_match_df.head()))
    table_df = pandas.merge(left=table_df, right=lanes_match_df, how='left', on=index_cols, suffixes=("","_temp"))
    table_df.loc[ pandas.isnull(table_df.county)&pandas.notnull(table_df.county_temp), "county"] = table_df.county_temp
    table_df.rename(columns={"lanes match_temp":"lanes match"}, inplace=True)
    table_df.drop(columns=["county_temp"], inplace=True)
    print("table_df head:\n{}".format(table_df.head()))

    # write non-wide
    write_tde(table_df, "%s.tde" % tde_file, arg_append=False)
    table_df.to_csv("%s.csv" % tde_file, index=False)

    # write wide
    write_tde(table_wide, "%s_wide.tde" % tde_file, arg_append=False)
    table_wide.to_csv("%s_wide.csv" % tde_file, index=False)